"""Crash real runner processes at side-effect boundaries; simulate only GitHub and agents."""

import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
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
    print(state.read_text())
elif args[:2] == ["pr", "create"]:
    assert not state.exists()
    assert "--draft" in args
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
        os.kill(os.getppid(), signal.SIGKILL)
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
        return self.factory("run", "--slice", "first", *options, ok=ok)

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
        self.crash_git("commit")
        self.start_run(ok=False)
        head = self.git(self.wt(), "rev-parse", "HEAD")
        self.assertEqual(self.journal()["phase"], "commit")
        self.factory("resume")
        self.assertEqual(self.git(self.wt(), "rev-list", "--count", "origin/main..HEAD"), "3")
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
    os.kill(os.getppid(), signal.SIGKILL)
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

    def test_draft_survives_lost_create_response(self):
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
        for conflict in ({"baseRefName": "release"}, {"isDraft": False}, {"state": "MERGED"}):
            self.pr.write_text(json.dumps(dict(json.loads(matching), **conflict)))
            self.assertIn("existing PR does not match", self.factory("resume", "--draft-pr", ok=False))
            self.reload()
            self.assertIsNone(self.data["slices"][0]["pr"])
        self.pr.write_text(matching)
        self.factory("resume", "--draft-pr")
        self.assertNotIn('"create"', self.pr.with_suffix(".calls").read_text())
        self.reload()
        self.assertEqual(self.data["slices"][0]["pr"], 17)

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


if __name__ == "__main__":
    unittest.main()
