"""Crash real runner processes at side-effect boundaries; simulate only GitHub and agents."""

import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import time
import unittest

FactoryFixture = runpy.run_path(str(Path(__file__).with_name("test-factory.py")))["FactoryFixture"]

GH = '''#!/usr/bin/env python3
import json, os, signal, sys
from pathlib import Path
args = sys.argv[1:]
state = Path(os.environ["FAKE_PR"])
log = state.with_suffix(".calls")
with log.open("a") as f:
    print(json.dumps(args), file=f)
target = "https://github.example/owner/a"
assert args[args.index("--repo") + 1] == os.environ["FIXTURE_ORIGIN"]
if args[:2] == ["pr", "list"]:
    print("[" + state.read_text() + "]" if state.exists() else "[]")
elif args[:2] == ["pr", "view"]:
    assert state.exists() and args[2] == "17"
    pr = json.loads(state.read_text())
    if "statusCheckRollup" in args[args.index("--json") + 1]:
        outcome = os.environ.get("CI_RESULT", "SUCCESS")
        pr["statusCheckRollup"] = [dict(__typename="CheckRun", name="required", workflowName="CI",
            status="COMPLETED", conclusion=outcome)] if outcome != "missing" else []
        if os.environ.get("DRIFT"):
            pr["headRefOid"] = "0" * 40
    print(json.dumps(pr))
elif args[:2] == ["pr", "ready"]:
    pr = json.loads(state.read_text())
    assert args[2] == "17" and pr["isDraft"]
    pr["isDraft"] = False
    state.write_text(json.dumps(pr))
    if os.environ.get("KILL_AFTER_READY"):
        os.kill(os.getppid(), signal.SIGKILL)

elif args[:2] == ["pr", "create"]:
    assert not state.exists() or json.loads(state.read_text())["state"] == "CLOSED"
    assert "--draft" in args
    assert args[args.index("--title")+1] == os.environ.get("EXPECT_TITLE", "feat(example): implement first")
    body = Path(args[args.index("--body-file")+1]).read_text()
    assert "Reviewed commit:" in body and "Create greeting.txt" in body
    branch = args[args.index("--head")+1]
    base = args[args.index("--base")+1]
    import subprocess
    head = subprocess.check_output(["git","--git-dir",os.environ["FIXTURE_ORIGIN"],
                                    "rev-parse","refs/heads/"+branch], text=True).strip()
    state.write_text(json.dumps(dict(number=17, url=target+"/pull/17", state="OPEN",
        isDraft=True, isCrossRepository=False, headRefOid=head, headRefName=branch, baseRefName=base)))
    if os.environ.get("KILL_AFTER_CREATE"):
        os.kill(os.getppid(), signal.SIGKILL)
    print(target+"/pull/17")
else:
    sys.exit("unexpected gh command")
'''

GIT = '''#!/usr/bin/env python3
import os, signal, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
rc = subprocess.run([os.environ["REAL_GIT"], *args]).returncode
marker = Path(os.environ["KILL_ONCE"])
if rc == 0 and marker.exists():
    action = marker.read_text()
    if action in args and (action != "checkout" or "-b" in args):
        marker.unlink()
        pid = int(os.environ["FIXTURE_RUNNER_PID"]) if action == "commit" else os.getppid()
        os.kill(pid, signal.SIGKILL)
sys.exit(rc)
'''


class RecoveryTests(FactoryFixture):
    def setUp(self):
        super().setUp()
        self.scripted()
        self.bin = self.base / "bin"
        self.pr = self.base / "pr.json"
        self.env.update(FAKE_PR=str(self.pr), FIXTURE_ORIGIN=str(self.base / "a.git"))
        self.shim("gh", GH)
        cfg = json.loads(self.cfg_path.read_text())
        cfg["ready_checks"]["a"] = ["CI / required"]
        self.cfg_path.write_text(json.dumps(cfg))

    def shim(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def crash_git(self, action):
        self.env["REAL_GIT"] = shutil.which("git")
        marker = self.base / "kill-once"
        marker.write_text(action)
        self.env["KILL_ONCE"] = str(marker)
        self.shim("git", GIT)

    def journal(self):
        path, = self.directory.glob(".factory-runs/first/run-*/journal.json")
        return json.loads(path.read_text())

    def start_run(self, *options, ok=True):
        binary = Path(__file__).resolve().parents[1] / "bin/factory"
        return self.call("sh", "-c", 'export FIXTURE_RUNNER_PID=$$; exec "$@"', "sh", binary,
                         "run", "example", "--slice", "first", *options, ok=ok, cwd=self.root)

    def test_interrupted_unregistered_checkout(self):
        self.crash_git("checkout")
        self.start_run("--draft-pr", ok=False)
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "planned")
        branch = self.git(self.wt(), "branch", "--show-current")
        self.assertEqual(branch, "codex/example-first")
        self.factory("resume", "--local-only")
        self.reload()
        self.assertEqual(self.data["slices"][0]["branch"], branch)
        self.assertEqual(self.data["slices"][0]["start_order"], 1)
        self.assertEqual(self.journal()["phase"], "local")
        self.assertFalse(self.pr.with_suffix(".calls").exists())

    def test_interrupted_commit_is_reused(self):
        hooks = self.base / "hooks"
        hooks.mkdir()
        for name, script in {"pre-commit": "echo formatted > formatted.txt\ngit add formatted.txt",
                             "commit-msg": """printf '\\nChange-Id: fixture\\n' >> "$1" """}.items():
            hook = hooks / name
            hook.write_text("#!/bin/sh\n" + script + "\n")
            hook.chmod(0o755)
        self.git(self.wt(), "config", "core.hooksPath", str(hooks))
        self.crash_git("commit")
        self.start_run(ok=False)
        head = self.git(self.wt(), "rev-parse", "HEAD")
        self.assertEqual(self.journal()["phase"], "commit")
        self.factory("resume")
        self.assertEqual(self.git(self.wt(), "rev-list", "--count", "origin/main..HEAD"), "3")
        self.assertEqual(self.git(self.wt(), "show", "HEAD:formatted.txt"), "formatted")
        self.assertIn("Change-Id: fixture", self.git(self.wt(), "log", "-1", "--format=%B"))
        self.git(self.wt(), "merge-base", "--is-ancestor", head, "HEAD")
        self.assertEqual(len(self.calls.read_text().splitlines()), 5)

    def test_interrupted_worker_keeps_lease_and_edits(self):
        builder = self.bin / "codex"
        source = builder.read_text()
        gate = self.base / "release"
        self.env["RELEASE_WORKER"] = str(gate)
        self.shim("codex", source.replace('if builder:\n    if', '''if builder and not Path("partial.txt").exists():
    import signal, time
    Path("partial.txt").write_text("work in progress")
    os.kill(int(os.environ["FIXTURE_RUNNER_PID"]), signal.SIGKILL)
    for _ in range(300):
        if Path(os.environ["RELEASE_WORKER"]).exists(): break
        time.sleep(0.1)
    sys.exit(0)
if builder:
    assert Path("partial.txt").read_text() == "work in progress"
    if'''))
        try:
            self.start_run(ok=False)
            self.assertEqual(self.journal()["phase"], "editing")
            self.assertIn("another operation is active", self.factory("resume", ok=False))
        finally:
            gate.touch()
        fd = os.open(self.directory / ".factory-runs", os.O_RDONLY)
        try:
            for _ in range(100):
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(0.05)
            else:
                self.fail("orphaned worker did not release the lease")
        finally:
            os.close(fd)
        self.factory("resume")
        self.assertEqual(self.git(self.wt(), "show", "HEAD:partial.txt"), "work in progress")

    def test_rejected_commit_blocks_after_bounded_repairs(self):
        hooks = self.base / "hooks"
        hooks.mkdir()
        attempts = self.base / "commit-attempts"
        self.env["COMMIT_ATTEMPTS"] = str(attempts)
        hook = hooks / "commit-msg"
        hook.write_text('#!/bin/sh\necho attempt >> "$COMMIT_ATTEMPTS"\necho "missing ticket trailer" >&2\nexit 1\n')
        hook.chmod(0o755)
        self.git(self.wt(), "config", "core.hooksPath", str(hooks))
        self.assertIn("missing ticket trailer", self.start_run(ok=False))
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "blocked")
        self.assertEqual(self.journal()["phase"], "blocked")
        self.assertIn("missing ticket trailer", self.data["slices"][0]["note"])
        self.assertEqual(self.git(self.wt(), "rev-parse", "HEAD"), self.journal()["base"])
        self.assertEqual(self.git(self.wt(), "diff", "--cached", "--name-only"), "greeting.txt")
        self.assertIn("missing ticket trailer", self.factory("resume", ok=False))
        limit = json.loads(self.cfg_path.read_text())["max_build_rounds"]
        self.assertEqual(attempts.read_text().splitlines(), ["attempt"] * limit)

    def test_builder_repairs_rejected_commit_message(self):
        hook = self.base / "hooks" / "commit-msg"
        hook.parent.mkdir()
        hook.write_text('#!/bin/sh\ngit interpret-trailers --parse "$1" | grep -qx "Ticket: EX-123" || '
                        '{ echo "ticket trailer required" >&2; exit 1; }\n')
        hook.chmod(0o755)
        self.git(self.wt(), "config", "core.hooksPath", str(hook.parent))
        builder = (self.bin / "codex").read_text()
        self.shim("codex", builder.replace('file.write_text("typo")', 'file.write_text("hello!")')
                  .replace('if os.environ.get("BAD_RESULT"):', '''if builder and "ticket trailer required" in prompt:
    import subprocess
    assert subprocess.check_output(["git", "show", ":greeting.txt"]) == b"hello!"
    result["summary"] = "Implement the greeting\\n\\nTicket: EX-123"
if os.environ.get("BAD_RESULT"):'''))
        self.start_run()
        self.assertEqual(self.journal()["round"], 2)
        self.assertEqual(self.journal()["phase"], "local")
        self.assertIn("Ticket: EX-123", self.git(self.wt(), "log", "-1", "--format=%B"))

    def test_commit_created_before_command_reports_failure(self):
        self.env["REAL_GIT"] = shutil.which("git")
        self.shim("git", '#!/bin/sh\ncase " $* " in\n'
                  '  *" commit "*) "$REAL_GIT" "$@" || exit $?; exit 1 ;;\n'
                  '  *) exec "$REAL_GIT" "$@" ;;\nesac\n')
        self.start_run()
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "review")
        self.assertEqual(self.git(self.wt(), "rev-list", "--count", "origin/main..HEAD"), "3")
        self.assertEqual(self.journal()["head"], self.git(self.wt(), "rev-parse", "HEAD"))

    def test_repaired_message_does_not_carry_into_review_repair(self):
        hook = self.base / "hooks" / "commit-msg"
        hook.parent.mkdir()
        hook.write_text('#!/bin/sh\nif git rev-parse HEAD:greeting.txt >/dev/null 2>&1; then exit 0; fi\n'
                        'grep -q "Ticket: EX-123" "$1" || { echo "ticket trailer required" >&2; exit 1; }\n')
        hook.chmod(0o755)
        self.git(self.wt(), "config", "core.hooksPath", str(hook.parent))
        builder = (self.bin / "codex").read_text()
        self.shim("codex", builder.replace('file.write_text("typo")', 'file.write_text("hello")')
                  .replace('if os.environ.get("BAD_RESULT"):', '''if builder and "ticket trailer required" in prompt:
    result["summary"] = "Repair the first commit\\n\\nTicket: EX-123"
if os.environ.get("BAD_RESULT"):'''))
        self.start_run()
        self.assertEqual(self.journal()["round"], 3)
        self.assertEqual(self.git(self.wt(), "log", "-1", "--format=%s"), "example: implement first (round 3)")
        self.assertIn("Ticket: EX-123", self.git(self.wt(), "show", "-s", "--format=%B", "HEAD~1"))

    def test_signing_timeout_and_refusals_retry_in_the_same_round(self):
        signer = shutil.which("ssh-keygen")
        if not signer or "gpg.ssh.allowedSignersFile" not in self.git(self.wt(), "help", "--config"):
            self.skipTest("Git SSH signing unavailable")
        key = self.base / "signing-key"
        self.call(signer, "-q", "-t", "ed25519", "-N", "", "-f", key)
        allowed = self.base / "signers"
        allowed.write_text("fixture " + key.with_suffix(".pub").read_text())
        gate = self.base / "wait-for-signer"
        gate.write_text("timeout")
        self.env.update(TEST_SIGNER=signer, SIGNER_GATE=str(gate))
        self.shim("test-signer", '#!/bin/sh\nif test -f "$SIGNER_GATE"; then\n'
                  '  if grep -q timeout "$SIGNER_GATE"; then exec sleep 60; fi\n'
                  '  echo "1Password: agent returned an error" >&2; exit 1\n'
                  'fi\nexec "$TEST_SIGNER" "$@"\n')
        for name, value in {"commit.gpgSign": "true", "gpg.format": "ssh", "user.signingKey": str(key),
                            "gpg.ssh.program": "test-signer", "gpg.ssh.allowedSignersFile": str(allowed)}.items():
            self.git(self.wt(), "config", name, value)
        cfg = json.loads(self.cfg_path.read_text())
        cfg["timeout_seconds"] = 4
        self.cfg_path.write_text(json.dumps(cfg))
        self.assertIn("git timed out", self.start_run(ok=False))
        self.assertEqual(self.journal()["phase"], "commit")
        calls = self.calls.read_bytes()
        gate.write_text("refused")
        hook = self.base / "hooks" / "pre-commit"
        hook.parent.mkdir()
        hook.write_text('#!/bin/sh\necho formatted > formatted.txt\ngit add formatted.txt\n')
        hook.chmod(0o755)
        self.git(self.wt(), "config", "core.hooksPath", str(hook.parent))
        for _ in range(2):
            output = self.factory("resume", ok=False)
            self.assertIn("1Password: agent returned an error", output)
            self.assertIn("Round 1 is preserved", output)
            self.reload()
            self.assertEqual(self.data["slices"][0]["status"], "implementing")
            checkpoint = self.journal()
            self.assertEqual((checkpoint["phase"], checkpoint["round"]), ("commit", 1))
            self.assertEqual(checkpoint["tree"], self.git(self.wt(), "write-tree"))
            self.assertEqual(self.calls.read_bytes(), calls)
        gate.unlink()
        self.factory("resume")
        self.git(self.wt(), "verify-commit", "HEAD")
        self.assertEqual(self.git(self.wt(), "show", "HEAD:formatted.txt"), "formatted")

    def test_draft_survives_lost_create_response(self):
        self.pr.write_text(json.dumps(dict(state="CLOSED", headRefName="codex/example-first", isCrossRepository=False)))
        self.env["KILL_AFTER_CREATE"] = "1"
        self.start_run("--draft-pr", ok=False)
        self.reload()
        self.assertIsNone(self.data["slices"][0]["pr"])
        calls = self.calls.read_bytes()
        report = json.loads(self.factory("status", "--remote", "--json"))
        self.assertEqual(report["slices"][0]["remote_pr"]["number"], 17)
        self.assertEqual(self.journal()["phase"], "publish")
        self.factory("resume")
        self.factory("resume")
        self.reload()
        s = self.data["slices"][0]
        self.assertEqual((s["status"], s["pr"]), ("review", 17))
        self.assertEqual(s["evidence"]["a1"]["commit"], json.loads(self.pr.read_text())["headRefOid"])
        requests = [json.loads(line)[:2] for line in self.pr.with_suffix(".calls").read_text().splitlines()]
        self.assertEqual(requests.count(["pr", "create"]), 1)
        self.assertEqual(self.calls.read_bytes(), calls)

    def test_promote_existing_legacy_draft_after_ci_and_lost_response(self):
        self.start_run("--draft-pr")
        calls = self.calls.read_bytes()
        journal, = self.directory.glob(".factory-runs/first/run-*/journal.json")
        old = self.journal()
        old.pop("pr_mode")
        journal.write_text(json.dumps(dict(old, draft=True)))
        self.factory("resume")
        self.assertTrue(json.loads(self.pr.read_text())["isDraft"])
        self.env["CI_RESULT"] = "FAILURE"
        self.assertIn("CI / required reported FAILURE", self.factory("resume", "--ready-pr", ok=False))
        self.assertEqual(self.journal()["phase"], "ci")
        self.assertTrue(json.loads(self.pr.read_text())["isDraft"])
        self.env.update(CI_RESULT="SUCCESS", KILL_AFTER_READY="1")
        self.factory("resume", ok=False)
        self.assertFalse(json.loads(self.pr.read_text())["isDraft"])
        self.assertIn("Ready for your review", self.factory("resume"))
        self.factory("resume")
        self.reload()
        row = self.data["slices"][0]
        self.assertEqual((row["status"], row["pr"], self.journal()["phase"]), ("review", 17, "ready"))
        self.assertNotIn("Draft PR:", row["note"])
        self.assertEqual(self.calls.read_bytes(), calls)
        commands = [json.loads(line)[:2] for line in self.pr.with_suffix(".calls").read_text().splitlines()]
        self.assertEqual(commands.count(["pr", "create"]), 1)
        self.assertEqual(commands.count(["pr", "ready"]), 1)

    def test_ready_run_waits_for_missing_gate_and_refuses_changed_head(self):
        self.env.update(CI_RESULT="missing", EXPECT_TITLE="fix(cli): correct the greeting")
        self.data["slices"][0]["pr_title"] = self.env["EXPECT_TITLE"]
        self.save()
        self.start_run("--draft-pr")
        cfg = json.loads(self.cfg_path.read_text())
        cfg["timeout_seconds"] = 1
        self.cfg_path.write_text(json.dumps(cfg))
        self.assertIn("still waiting for CI / required", self.factory("resume", "--ready-pr", ok=False))
        self.env.update(CI_RESULT="SUCCESS", DRIFT="1")
        self.assertIn("reviewed commit", self.factory("resume", ok=False))
        self.assertTrue(json.loads(self.pr.read_text())["isDraft"])
        self.factory("resume", "--local-only")
        self.factory("resume")
        self.assertTrue(json.loads(self.pr.read_text())["isDraft"])

    def test_ready_run_creates_and_promotes(self):
        preview = self.factory("plan", "--ready-pr")
        self.assertIn("wait for CI / required", preview)
        self.assertIn("Ready for your review", self.factory("run", "--ready-pr"))
        pr = json.loads(self.pr.read_text())
        self.assertFalse(pr["isDraft"])
        self.assertEqual(pr["headRefOid"], self.journal()["head"])

    def test_interrupt_after_push_then_change_handoff(self):
        self.crash_git("push")
        self.start_run("--draft-pr", ok=False)
        self.assertFalse(self.pr.exists())
        self.assertEqual(self.journal()["phase"], "publish")
        self.factory("resume", "--local-only")
        self.assertEqual(self.journal()["phase"], "local")
        self.assertFalse(self.pr.exists())
        self.factory("resume", "--draft-pr")
        self.assertEqual(self.journal()["phase"], "drafted")

    def test_opt_in_after_local_handoff_and_reuse(self):
        self.start_run()
        self.factory("resume", "--local-only")
        self.assertFalse(self.pr.with_suffix(".calls").exists())
        self.reload()
        s = self.data["slices"][0]
        head = self.git(self.wt(), "rev-parse", "HEAD")
        self.git(self.wt(), "push", "origin", s["branch"])
        self.pr.write_text(json.dumps(dict(number=17, state="OPEN", isDraft=True, isCrossRepository=False,
                                           url="https://github.example/owner/a/pull/17", headRefName=s["branch"],
                                           headRefOid=head, baseRefName="main")))
        matching = self.pr.read_text()
        for conflict in ({"baseRefName": "release"}, {"isDraft": False}):
            self.pr.write_text(json.dumps(dict(json.loads(matching), **conflict)))
            self.assertIn("existing PR does not match", self.factory("resume", "--draft-pr", ok=False))
            self.reload()
            self.assertIsNone(self.data["slices"][0]["pr"])
        self.pr.write_text(json.dumps(dict(json.loads(matching), state="MERGED")))
        self.assertIn("already merged", self.factory("resume", "--draft-pr", ok=False))
        self.pr.write_text(matching)
        self.factory("resume", "--draft-pr")
        self.assertNotIn('"create"', self.pr.with_suffix(".calls").read_text())
        self.reload()
        self.assertEqual(self.data["slices"][0]["pr"], 17)
        self.pr.unlink()
        self.assertIn("Cannot read recorded PR #17", self.factory("resume", "--draft-pr", ok=False))
        self.assertNotIn('"create"', self.pr.with_suffix(".calls").read_text())

    def test_legacy_review_requires_explicit_publish_and_current_evidence(self):
        self.start()
        self.change()
        self.verified()
        self.data["slices"][0]["status"] = "review"
        self.save()
        self.factory("resume")
        self.assertFalse(self.pr.with_suffix(".calls").exists())
        self.data["working_agreement"] = "Push the reviewed slice and open its draft."
        self.save()
        self.assertIn("working agreement changed", self.factory("resume", ok=False))
        self.factory("resume", "--draft-pr")
        self.assertFalse(self.calls.exists())
        self.reload()
        self.assertEqual(self.data["slices"][0]["pr"], 17)

    def test_refuse_unrelated_remote_and_stale_review(self):
        self.start_run()
        self.reload()
        branch = self.data["slices"][0]["branch"]
        seed = self.seeds["a"]
        (seed / "other").write_text("different")
        self.git(seed, "add", "other")
        self.git(seed, "commit", "-m", "someone else's work")
        self.git(seed, "push", "origin", "HEAD:" + branch)
        self.assertIn("refusing to overwrite", self.factory("resume", "--draft-pr", ok=False))
        self.assertEqual(self.git(seed, "ls-remote", "origin", "refs/heads/" + branch).split()[0],
                         self.git(seed, "rev-parse", "HEAD"))
        self.change()
        self.assertIn("commit changed", self.factory("resume", ok=False))
        self.assertFalse(self.pr.exists())

    def test_legacy_partial_edits_require_ownership(self):
        self.start()
        (self.directory / ".factory-runs/first/run-old/round-1").mkdir(parents=True)
        (self.wt() / "partial.txt").write_text("legacy edit")
        self.assertIn("--adopt-edits", self.factory("resume", ok=False))
        self.factory("resume", "--adopt-edits")
        self.assertEqual(self.git(self.wt(), "show", "HEAD:partial.txt"), "legacy edit")


class WorkerLeaseTests(unittest.TestCase):
    def test_background_descendant_cannot_keep_lease(self):
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "factory"))
        from agents import process
        from delivery import exclusive
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            marker = directory / "keep-running"
            marker.touch()
            # Fork and detach without closing descriptors, as a native tool can.
            script = """import os, time
from pathlib import Path
if os.fork() == 0:
    os.setsid()
    for i in range(200):
        if not Path('keep-running').exists(): break
        time.sleep(.05)
    os._exit(0)
"""
            try:
                with exclusive(directory):
                    self.assertEqual(process([sys.executable, "-c", script], directory, "", directory / "log", 5), 0)
                with exclusive(directory):
                    pass
            finally:
                marker.unlink()


if __name__ == "__main__":
    unittest.main()
