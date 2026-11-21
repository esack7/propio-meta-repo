"""Factory integration tests with local remotes. Opt in to paid CLIs via FACTORY_LIVE_PROFILE."""

import json
import os
from pathlib import Path
import runpy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
WorkflowFixture = runpy.run_path(str(ROOT / "tests/test-delivery.py"))["WorkflowFixture"]

# Exercise the actual CLI argument and response boundaries for both adapters.
AGENT = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
claude = Path(sys.argv[0]).name == "claude"
builder = prompt.startswith("Implement only")
if claude:
    assert "--restricted" in args and "--strict-mcp-config" in args and "-p" in args
    tools = args[args.index("--tools")+1].split(",")
    assert ("Edit" in tools) == builder and "Bash" not in tools
else:
    assert args[args.index("--sandbox")+1] == ("workspace-write" if builder else "read-only")
with open(os.environ["FACTORY_CALLS"], "a") as f:
    invocation = [Path(sys.argv[0]).name]
    if "--model" in args:
        invocation.append(args[args.index("--model") + 1])
    print(*invocation, "build" if builder else "review", file=f)
file = Path("greeting.txt")
if builder:
    if "repair the punctuation" in prompt:
        file.write_text("hello!")
    elif "word must be hello" in prompt.split("Previous feedback:")[-1]:
        file.write_text("hello")
    else:
        file.write_text("typo")
    result = dict(outcome="built", summary="Updated the greeting.")
else:
    assert "check_results" in prompt and "diff --git" in prompt
    result = (dict(outcome="approve", summary="Greeting verified.") if file.read_text()=="hello!"
              else dict(outcome="changes", summary="repair the punctuation"))
if os.environ.get("BAD_RESULT"):
    result = {"summary": "incomplete"}
if claude:
    print(json.dumps(dict(subtype="success", is_error=False, structured_output=result)))
else:
    Path(args[args.index("-o")+1]).write_text(json.dumps(result))
'''


class FactoryFixture(WorkflowFixture):
    def setUp(self):
        super().setUp()
        directory = self.root / "factory"
        directory.mkdir()
        self.cfg_path = directory / "config.json"
        cfg = json.loads((ROOT / "factory/config.json").read_text())
        cfg.update(repo_checks={"a": [[sys.executable, "-c", "pass"]]}, timeout_seconds=180)
        self.cfg_path.write_text(json.dumps(cfg))
        self.map.write_text(self.map.read_text().replace("    git:", '    context: ["README.md"]\n    git:'))
        self.data["criteria"]["a1"] = "Create greeting.txt containing exactly hello!"
        self.data["slices"][0]["factory_checks"] = {"a1": [[
            sys.executable, "-c", "from pathlib import Path; assert Path('greeting.txt').read_text().startswith('hello'), 'word must be hello'"
        ]]}
        for name in ("requirements.md", "design.md", "tasks.md"):
            (self.directory / name).write_text("Create greeting.txt containing exactly hello! with no newline.")
        self.save()
        self.calls = self.base / "calls"
        self.env["FACTORY_CALLS"] = str(self.calls)

    def scripted(self):
        shim = self.base / "bin"
        shim.mkdir()
        for name in ("claude", "codex"):
            path = shim / name
            path.write_text(AGENT)
            path.chmod(0o755)
        self.env["PATH"] = str(shim) + os.pathsep + self.env["PATH"]

    def factory(self, verb, *args, ok=True):
        return self.call(ROOT / "bin/factory", verb, "example", *args, cwd=self.root, ok=ok)


class FactoryTests(FactoryFixture):
    def test_preview(self):
        self.scripted()
        # Reference context for a second repo may use full YAML block syntax.
        self.map.write_text(self.map.read_text().replace(
            '  - name: b\n    context: ["README.md"]',
            '  - name: b\n    context:\n      - "Team notes.md"\n      - README.md'))
        (self.ref("b") / "Team notes.md").write_text("Fixture context")
        paths = [self.state_path, Path(self.git(self.wt(), "rev-parse", "--absolute-git-dir")) / "index"]
        before = [p.stat().st_mtime_ns for p in paths]
        p = json.loads(self.factory("plan", "--json"))
        self.assertEqual(p["repository_context"], [
            str(self.wt() / "README.md"), str(self.ref("b") / "Team notes.md"),
            str(self.ref("b") / "README.md")])
        self.assertEqual(p["blockers"], [])
        self.assertEqual(p["roles"], {
            "builder": {"agent": "codex", "model": "gpt-6.1-sol"},
            "reviewer": {"agent": "claude", "model": "claude-opus-5-5"},
        })
        self.assertEqual(before, [p.stat().st_mtime_ns for p in paths])
        self.assertFalse(self.calls.exists())
        self.assertFalse((self.directory / ".factory-runs").exists())
        self.data["slices"].append(self.slice("second", "b", ["first"]))
        self.save()
        self.assertIn("first must merge first", self.factory("plan", "--slice", "second"))
        self.assertIn("resolve the preview blockers", self.factory("run", "--slice", "second", ok=False))
        self.assertFalse(self.calls.exists())

    def assert_success(self, profile):
        out = self.factory("run", "--slice", "first", "--profile", profile)
        self.assertIn("Review handoff", out)
        self.reload()
        s = self.data["slices"][0]
        self.assertEqual(s["status"], "review")
        self.assertEqual(s["evidence"]["a1"]["commit"], self.git(self.wt(), "rev-parse", "HEAD"))
        self.assertEqual((self.wt() / "greeting.txt").read_text(), "hello!")
        self.assertFalse((self.ref() / "greeting.txt").exists())
        self.assertIsNone(s["pr"])
        self.assertEqual(self.git(self.wt(), "status", "--porcelain"), "")
        self.assertEqual(self.git(self.wt(), "ls-remote", "--heads", "origin", s["branch"]), "")

    def matrix(self, profile, builder, reviewer):
        self.scripted()
        self.assert_success(profile)
        self.assertEqual(self.calls.read_text().splitlines(),
                         [builder + " build", builder + " build", reviewer + " review",
                          builder + " build", reviewer + " review"])

    def test_mixed(self):
        self.matrix("mixed", "codex gpt-6.1-sol", "claude claude-opus-5-5")

    def test_claude(self):
        self.matrix("claude", "claude", "claude")

    def test_codex(self):
        self.matrix("codex", "codex", "codex")

    def test_exhausted(self):
        self.scripted()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["max_build_rounds"] = 1
        self.cfg_path.write_text(json.dumps(cfg))
        self.assertIn("round limit reached", self.factory("run", "--slice", "first", ok=False))
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "blocked")
        self.assertEqual(self.data["slices"][0]["evidence"], {})
        self.assertNotIn("review", self.calls.read_text())

    def test_bad_payload(self):
        self.scripted()
        self.env["BAD_RESULT"] = "1"
        self.assertIn("invalid structured response", self.factory("run", "--slice", "first", ok=False))
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "blocked")
        self.assertTrue((self.wt() / "greeting.txt").exists())

    def test_delivery_edit_during_check_is_preserved(self):
        self.scripted()
        # Simulate a concurrent operator editing the plan before the review handoff.
        edit = ("import json, pathlib; p=pathlib.Path(" + repr(str(self.state_path)) + "); "
                "data=json.loads(p.read_text()); data['slices'][0]['note']='operator edit'; "
                "p.write_text(json.dumps(data))")
        cfg = json.loads(self.cfg_path.read_text())
        cfg["repo_checks"]["a"] = [[sys.executable, "-c", edit]]
        self.cfg_path.write_text(json.dumps(cfg))
        out = self.factory("run", "--slice", "first", ok=False)
        self.assertIn("delivery record changed", out)
        self.reload()
        self.assertEqual(self.data["slices"][0]["note"], "operator edit")
        self.assertEqual(self.data["slices"][0]["evidence"], {})

    def test_no_review_evidence_on_dirty_check(self):
        self.scripted()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["max_build_rounds"] = 1
        cfg["repo_checks"]["a"] = [[sys.executable, "-c",
                                    "from pathlib import Path; Path('README.md').write_text('dirty')"]]
        self.cfg_path.write_text(json.dumps(cfg))
        output = self.factory("run", "--slice", "first", ok=False)
        self.assertIn("checks left changes", output)
        self.assertIn("README.md", output)
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "blocked")
        self.assertEqual(self.data["slices"][0]["evidence"], {})
        self.assertEqual((self.wt() / "README.md").read_text(), "dirty")

    def test_builder_repairs_check_outputs(self):
        self.scripted()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["repo_checks"]["a"] = [[sys.executable, "-c",
            "from pathlib import Path; Path('coverage.tmp').write_text('generated')"]]
        self.cfg_path.write_text(json.dumps(cfg))
        builder = self.base / "bin/codex"
        builder.write_text(builder.read_text().replace('file.write_text("typo")', 'file.write_text("hello!")')
                           .replace('if os.environ.get("BAD_RESULT"):', '''if builder and "checks left changes" in prompt:
    assert "?? coverage.tmp" in prompt and Path("coverage.tmp").read_text() == "generated"
    Path(".gitignore").write_text("coverage.tmp\\n")
if os.environ.get("BAD_RESULT"):'''))
        self.assert_success("mixed")
        self.assertEqual(self.git(self.wt(), "ls-files", "coverage.tmp"), "")
        self.assertEqual(len(self.calls.read_text().splitlines()), 3)

    def test_missing_check_records_blocker(self):
        self.scripted()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["repo_checks"]["a"] = [["missing-factory-test-executable"]]
        cfg["max_build_rounds"] = 1
        self.cfg_path.write_text(json.dumps(cfg))
        self.factory("run", "--slice", "first", ok=False)
        self.reload()
        self.assertEqual(self.data["slices"][0]["status"], "blocked")
        self.assertIn("Cannot launch missing-factory-test-executable", self.data["slices"][0]["note"])

    @unittest.skipUnless(os.environ.get("FACTORY_LIVE_PROFILE"), "opt-in authenticated CLI smoke")
    def test_live(self):
        # Fully synthetic prompt and local remotes. Enforce the exact expected final content.
        profile = os.environ["FACTORY_LIVE_PROFILE"]
        cfg = json.loads(self.cfg_path.read_text())
        for role, selection in cfg["profiles"][profile].items():
            agent = selection if isinstance(selection, str) else selection["agent"]
            model = os.environ.get(f"FACTORY_LIVE_{agent.upper()}_MODEL")
            if model:
                cfg["profiles"][profile][role] = {"agent": agent, "model": model}
        self.cfg_path.write_text(json.dumps(cfg))
        self.data["slices"][0]["factory_checks"]["a1"][0][-1] = (
            "from pathlib import Path; assert Path('greeting.txt').read_bytes() == b'hello!'")
        self.save()
        self.assert_success(profile)


if __name__ == "__main__":
    unittest.main()
