"""Spec-level CLI pilot using two real Git remotes and a locally packed npm package."""

import json
from pathlib import Path
import runpy
import shutil
import sys
import unittest

FactoryFixture = runpy.run_path(str(Path(__file__).with_name("test-factory.py")))["FactoryFixture"]


class SpecTests(FactoryFixture):
    def setUp(self):
        super().setUp()
        self.scripted()
        self.env["npm_config_cache"] = str(self.base / "npm-cache")
        self.env["npm_config_offline"] = "true"
        self.data["criteria"]["b1"] = "Consumer uses the producer greeting"
        consumer = self.slice("second", "b", ["first"])
        consumer.update(criteria=["b1"], factory_checks={"b1": [[sys.executable, "-c",
            "from pathlib import Path; assert Path('greeting.txt').read_text().startswith('hello'), 'word must be hello'"]]})
        self.data["slices"].append(consumer)
        self.save()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["repo_checks"]["b"] = []
        self.cfg_path.write_text(json.dumps(cfg))

    def packages(self):
        producer, consumer = self.seeds["a"], self.seeds["b"]
        (producer / "package.json").write_text(json.dumps(dict(name="fixture-greeting", version="1.0.0",
            main="index.js", scripts={"build": "node --check index.js"})))
        (producer / "index.js").write_text("module.exports = require('fs').readFileSync(__dirname + '/greeting.txt','utf8')")
        (producer / "greeting.txt").write_text("old")
        self.call("npm", "install", "--package-lock-only", "--no-audit", cwd=producer)
        packed = json.loads(self.call("npm", "pack", "--json", "--pack-destination", self.base, cwd=producer))
        dependency = "file:" + str(self.base / packed[0]["filename"])
        (consumer / "package.json").write_text(json.dumps(dict(name="fixture-app", version="1.0.0",
            scripts={"test": "node test.js"}, dependencies={"fixture-greeting": dependency})))
        (consumer / "test.js").write_text(
            "const assert = require('assert'); const api = require('fixture-greeting');\n"
            "assert.strictEqual(api, 'hello!');\n"
            "assert.ok(api.startsWith(require('fs').readFileSync('greeting.txt', 'utf8')));\n")
        self.call("npm", "install", "--package-lock-only", "--no-audit", cwd=consumer)
        for seed in self.seeds.values():
            self.git(seed, "add", ".")
            self.git(seed, "commit", "-m", "seed packages")
            self.git(seed, "push", "origin", "main")
        self.data["slices"][1]["package_checks"] = [{"producer_slice": "first", "checks": ["test"]}]
        self.save()

    def squash(self, repo):
        seed = self.seeds[repo]
        self.git(seed, "fetch", str(self.wt(repo)), "HEAD")
        self.git(seed, "merge", "--squash", "FETCH_HEAD")
        self.git(seed, "commit", "-m", "squash reviewed work")
        self.git(seed, "push", "origin", "main")
        return self.git(seed, "rev-parse", "HEAD")

    def verify(self, complete=False):
        report = json.loads(self.factory("verify", "--json", ok=complete))
        self.assertEqual(report["verified"], complete)
        return report

    @unittest.skipUnless(shutil.which("npm"), "npm unavailable")
    def test_producer_consumer_pilot(self):
        self.packages()
        self.factory("run")
        self.reload()
        producer, consumer = self.data["slices"]
        self.assertEqual([producer["status"], consumer["status"]], ["review", "planned"])
        self.assertIn("first", self.verify()["waiting"]["second"])
        head = self.git(self.wt(), "rev-parse", "HEAD")
        integrated = self.squash("a")
        self.assertNotEqual(head, integrated)
        self.fake_gh(state="OPEN", mergeCommit=None)
        self.assertIn("open", self.verify()["waiting"]["first"])
        self.fake_gh(mergeCommit={"oid": integrated})
        self.factory("run")
        self.reload()
        producer, consumer = self.data["slices"]
        self.assertEqual([producer["status"], consumer["status"]], ["verified", "review"])
        proof = producer["merge_evidence"]
        self.assertEqual((proof["pr"], proof["head"], proof["commit"]), (1, head, integrated))
        candidate = self.git(self.wt("b"), "rev-parse", "HEAD")
        package, = consumer["package_evidence"]
        self.assertEqual((package["producer_commit"], package["consumer_commit"]), (integrated, candidate))
        self.assertRegex(package["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(package["passed"])
        calls = self.calls.read_bytes()
        self.assertEqual(self.verify()["verified_slices"], ["first"])
        consumer_merge = self.squash("b")
        self.assertNotEqual(candidate, consumer_merge)
        consumer["pr"] = 2
        self.save()
        fixture = self.base / "gh-consumer.json"
        fixture.write_text(json.dumps(dict(state="MERGED", isCrossRepository=False, headRefName=consumer["branch"],
            headRefOid=candidate, baseRefName="main", mergeCommit={"oid": consumer_merge}, url="https://example.test/pull/2")))
        self.env["GH_CONSUMER_FIXTURE"] = str(fixture)
        (self.base / "bin/gh").write_text('#!/bin/sh\ncase "$3" in\n1) cat "$GH_FIXTURE";;\n'
                                         '2) cat "$GH_CONSUMER_FIXTURE";;\n*) exit 1;;\nesac\n')
        report = self.verify(complete=True)
        self.assertEqual(report["criteria"], {"a1": ["first"], "b1": ["second"]})
        delivered, = report["evidence"]["second"]["packages"]
        self.assertEqual((delivered["producer_commit"], delivered["consumer_commit"]), (integrated, consumer_merge))
        self.assertEqual(delivered["checks"], ["test"])
        before = self.state_path.read_bytes()
        self.assertIn("VERIFIED", self.factory("run"))
        self.assertEqual(before, self.state_path.read_bytes())
        self.assertEqual(calls, self.calls.read_bytes())
        # Published compatibility is a distinct gate. The locked file dependency
        # cannot satisfy it. Even a manually selected successor stays blocked.
        self.reload()
        self.data["slices"][1]["package_checks"][0]["mode"] = "published"
        self.data["slices"].append(self.slice("third", "a", ["second"]))
        self.save()
        before = self.state_path.read_bytes()
        report = self.verify()
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertIn("published package check failed", report["issues"]["second"])
        self.assertIn("second", report["waiting"]["third"])
        self.assertIn("missing current published package evidence", self.factory("run", "--slice", "third", ok=False))
        self.assertIn("missing current published package evidence", self.engine("start", "third", ok=False))
        self.assertEqual(calls, self.calls.read_bytes())
        # A later branch commit invalidates the retained PR head and its dependents.
        self.change()
        report = self.verify()
        self.assertEqual(report["verified_slices"], [])
        self.assertIn("PR head differs", report["issues"]["first"])
        self.assertIn("first", report["waiting"]["second"])

    def test_independent_slices_and_revised_acceptance(self):
        self.data["slices"][1]["depends_on"] = []
        self.data["criteria"]["unassigned"] = "Still needs an owner"
        self.save()
        self.factory("run")
        self.reload()
        self.assertEqual([s["status"] for s in self.data["slices"]], ["review", "review"])
        for name in self.seeds:
            self.git(self.wt(name), "push", "origin", "HEAD:main")
        self.assertIn("unassigned: no verified slice", self.verify()["acceptance_gaps"])
        self.reload()
        del self.data["criteria"]["unassigned"]
        self.data["criteria"]["a1"] = "A different requirement"
        self.save()
        self.assertIn("changed after review", self.verify()["issues"]["first"])

    def test_manual_merge_unlocks_work_without_certifying_acceptance(self):
        self.start()
        self.change()
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.data["slices"][0]["status"] = "merged"
        # Reuse the same repository to exercise both the busy-repo and dependency gates.
        self.data["slices"][1]["repo"] = "a"
        self.save()
        before = self.state_path.read_bytes()
        report = self.verify()
        self.assertEqual(report["eligible_predecessors"], ["first"])
        self.assertEqual(report["verified_slices"], [])
        self.assertEqual(self.state_path.read_bytes(), before)
        self.factory("run")
        self.reload()
        self.assertEqual(self.data["slices"][1]["status"], "review")
        self.assertNotIn("merge_evidence", self.data["slices"][0])

    def test_dirty_verification_preserves_passing_record(self):
        self.start()
        self.change()
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.verified()
        self.assertEqual(self.verify()["verified_slices"], ["first"])
        before = self.state_path.read_bytes()
        notes = self.wt() / "local-notes"
        notes.write_text("keep")
        report = self.verify()
        self.assertIn("uncommitted", report["issues"]["first"])
        self.assertEqual(report["eligible_predecessors"], [])
        self.assertEqual(self.state_path.read_bytes(), before)
        notes.unlink()
        self.assertEqual(self.verify()["verified_slices"], ["first"])

    def test_verified_middle_slice_with_manual_ancestor_unlocks_successor(self):
        self.start()
        self.change()
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.data["slices"][0]["status"] = "merged"
        self.save()
        self.engine("start", "second")
        head = self.change("b")
        self.git(self.wt("b"), "push", "origin", "HEAD:main")
        self.reload()
        self.data["slices"][1].update(status="verified", evidence={"b1": {"commit": head, "check": "passed"}})
        third = self.slice("third", "b", ["second"])
        third["factory_checks"] = self.data["slices"][0]["factory_checks"]
        self.data["slices"].append(third)
        self.save()
        report = self.verify()
        self.assertEqual(report["eligible_predecessors"], ["first", "second"])
        self.assertEqual(report["verified_slices"], ["second"])
        marker = self.wt("b") / "dirty"
        marker.touch()
        self.assertEqual(self.verify()["eligible_predecessors"], ["first"])
        marker.unlink()
        self.factory("run")
        self.reload()
        self.assertEqual([s["status"] for s in self.data["slices"]], ["merged", "verified", "review"])

    @unittest.skipUnless(shutil.which("npm"), "npm unavailable")
    def test_failed_package_check_keeps_consumer_out_of_review(self):
        self.packages()
        self.data["slices"][1]["package_checks"][0]["checks"] = ["missing-script"]
        self.data["slices"][1]["factory_checks"]["b1"] = [["git", "ls-files", "--error-unmatch", "greeting.txt"]]
        self.save()
        self.start()
        (self.wt() / "greeting.txt").write_text("hello!")
        self.git(self.wt(), "commit", "-am", "implement producer greeting")
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.verified()
        output = self.factory("run", ok=False)
        self.reload()
        self.assertIn("package check failed", output)
        self.assertEqual(self.data["slices"][1]["status"], "blocked")
        self.assertEqual(self.data["slices"][1]["evidence"], {})
        self.assertNotIn("review", self.calls.read_text())

    def test_exact_pr_and_fresh_fetch_required(self):
        self.start()
        head = self.change()
        self.verified()
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.fake_gh(isCrossRepository=True, mergeCommit={"oid": head})
        self.assertIn("mismatch", self.verify()["issues"]["first"])
        self.fake_gh(mergeCommit={"oid": "0" * 40})
        self.assertIn("absent", self.verify()["issues"]["first"])
        self.fake_gh(mergeCommit={"oid": head})
        self.assertEqual(self.verify()["verified_slices"], ["first"])
        (self.base / "a.git").rename(self.base / "unavailable.git")
        report = self.verify()
        self.assertEqual(report["verified_slices"], [])
        self.assertIn("could not fetch", report["issues"]["first"])

    @unittest.skipUnless(shutil.which("npm"), "npm unavailable")
    def test_package_check_worktree_changes_get_repaired(self):
        self.packages()
        seed = self.seeds["b"]
        target = self.wt("b") / "package-output.tmp"
        once = self.base / "package-wrote-output"
        script = seed / "test.js"
        script.write_text(script.read_text() + "\nconst fs = require('fs');\n" +
                          f"if (!fs.existsSync({json.dumps(str(once))})) {{\n" +
                          f"fs.writeFileSync({json.dumps(str(target))}, 'generated');\n" +
                          f"fs.writeFileSync({json.dumps(str(once))}, 'done');\n}}\n")
        self.git(seed, "add", "test.js")
        self.git(seed, "commit", "-m", "package check output fixture")
        self.git(seed, "push", "origin", "main")
        self.start()
        (self.wt() / "greeting.txt").write_text("hello!")
        self.git(self.wt(), "add", "greeting.txt")
        self.git(self.wt(), "commit", "-m", "producer")
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.verified()
        builder = self.base / "bin/codex"
        builder.write_text(builder.read_text().replace('file.write_text("typo")', 'file.write_text("hello!")')
                           .replace('if os.environ.get("BAD_RESULT"):', '''if builder and "checks left changes" in prompt:
    assert "package-output.tmp" in prompt
    Path(".gitignore").write_text("package-output.tmp\\n")
if os.environ.get("BAD_RESULT"):'''))
        self.factory("run", "--slice", "second")
        self.reload()
        self.assertEqual(self.data["slices"][1]["status"], "review")
        self.assertEqual(self.git(self.wt("b"), "ls-files", "package-output.tmp"), "")
        self.assertEqual(target.read_text(), "generated")

    @unittest.skipUnless(shutil.which("npm"), "npm unavailable")
    def test_package_timeout_returns_to_builder(self):
        self.packages()
        script = self.seeds["b"] / "test.js"
        script.write_text(script.read_text() + "\nif (require('fs').readFileSync('behavior.txt', 'utf8') === 'hang') {\n"
                          "console.log('package waiting for fix'); setInterval(() => {}, 1000); }\n")
        self.git(self.seeds["b"], "add", "test.js")
        self.git(self.seeds["b"], "commit", "-m", "package timeout fixture")
        self.git(self.seeds["b"], "push", "origin", "main")
        self.start()
        (self.wt() / "greeting.txt").write_text("hello!")
        self.git(self.wt(), "add", "greeting.txt")
        self.git(self.wt(), "commit", "-m", "producer")
        self.git(self.wt(), "push", "origin", "HEAD:main")
        self.verified()
        cfg = json.loads(self.cfg_path.read_text())
        cfg["timeout_seconds"] = 15
        self.cfg_path.write_text(json.dumps(cfg))
        builder = self.base / "bin/codex"
        builder.write_text(builder.read_text().replace('file.write_text("typo")', 'file.write_text("hello!")')
                           .replace('if os.environ.get("BAD_RESULT"):', '''if builder:
    if "package check timed out" in prompt:
        Path("behavior.txt").write_text("fixed")
    else:
        Path("behavior.txt").write_text("hang")
if os.environ.get("BAD_RESULT"):'''))
        self.factory("run", "--slice", "second")
        self.reload()
        self.assertEqual(self.data["slices"][1]["status"], "review")
        self.assertEqual((self.wt("b") / "behavior.txt").read_text(), "fixed")


if __name__ == "__main__":
    unittest.main()
