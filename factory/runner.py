"""Build, review, resume, and verify multi-repository delivery slices."""

import argparse
import json
import os
from pathlib import Path
from copy import deepcopy
import shlex
import shutil
import sys
import tempfile

from agents import AgentUnavailable, BuilderFeedback, FactoryError, invoke, process, tail
from delivery import Delivery, eligible_predecessor, exclusive, git, run
from drafts import lookup, promote, publish, verify_pr
from journal import Journal, run_root
from package_evidence import require_reports
from spec_delivery import package_reports, package_sources, reconcile, show_verification
from planning import context_files, helper, plan, print_plan

BUILD = """Implement only this slice in the current worktree. You own source edits.
The runner commits, runs the listed checks, and invokes the reviewer. Leave git,
delivery state, and external services to the runner. Address any previous feedback.
Report built with a summary, or blocked with the outstanding question.
List exact repository-relative files intentionally kept as source changes in
intended_files, including snapshots or generated source that belongs in the commit.
Use an empty list when there are no such files."""
REVIEW = """Independently review the complete candidate diff against the supplied criteria,
design, and repository instructions. Inspect the worktree read-only as needed.
Assess whether the checks actually exercise each criterion and whether tests were weakened.
Assess whether files claimed in intended_files belong in the source change.
Report approve with a rationale, changes with specific actionable findings tied to
criteria or concrete defects, or blocked with the question that requires a decision."""


def ensure_head(wt, branch, expected, clean=False):
    if git(wt, "symbolic-ref", "--short", "HEAD") != branch or git(wt, "rev-parse", "HEAD") != expected:
        raise FactoryError("the checked-out branch or commit changed unexpectedly; inspect the worktree")
    if clean:
        changes = git(wt, "status", "--porcelain", "--untracked-files=all")
        if changes:
            raise FactoryError(f"the candidate worktree changed during verification; inspect the edits:\n{changes}")


def check_candidate(wt, head, checks, directory, timeout):
    results = {}
    for group in checks.values():
        for argv in group:
            name = shlex.join(argv)
            if name in results:
                continue
            log = directory / f"check-{len(results) + 1}.log"
            print("Check:", name, flush=True)
            try:
                rc = process(argv, wt, "", log, timeout)
            except AgentUnavailable as exc:
                results[name] = {"exit": 124, "timed_out": True, "log": log.name}
                (directory / "checks.json").write_text(json.dumps({"commit": head, "results": results}, indent=2))
                return results, f"{name} timed out after {timeout}s. {exc}\n{tail(log)}"
            results[name] = {"exit": rc, "log": log.name}
            record = {"commit": head, "results": results}
            (directory / "checks.json").write_text(json.dumps(record, indent=2))
            if rc:
                return results, f"{name} failed (exit {rc}).\n{tail(log)}"
    return results, ""


def slice_in(data, sid):
    s = next((s for s in data["slices"] if s["id"] == sid), None)
    if s is None:
        raise FactoryError(f"{sid}: missing slice in delivery record")
    return s


def adopt_legacy(d, sid, adopt_edits, profile):
    data = d.load()
    eligible = [s for s in data["slices"] if s.get("branch") and (sid is None or sid == s["id"])
                and (s["status"] in {"implementing", "review"} or
                     (s["status"] == "blocked" and s["note"].startswith("interrupted\n")))]
    if len(eligible) != 1:
        raise FactoryError("no unique recoverable slice; inspect factory status and select --slice")
    s = eligible[0]
    sid, repo = s["id"], s["repo"]
    _, wt = d.registered_worktree(repo)
    head = git(wt, "rev-parse", "HEAD")
    ensure_head(wt, s["branch"], head, clean=s["status"] == "review")
    if s["status"] == "review":
        if (set(s["evidence"]) != set(s["criteria"]) or
                any(e["commit"] != head for e in s["evidence"].values())):
            raise FactoryError("the existing review evidence does not cover this commit")
        p = dict(spec=d.spec, slice=sid, repository=repo)
        return Journal.create(d, data, {}, p, "local", phase="local", head=head)
    prior = list((run_root(d) / sid).glob("run-*"))
    if len(prior) != 1 or prior[0].resolve() != prior[0]:
        raise FactoryError("cannot identify the prior factory attempt; inspect the worktree")
    # A pre-journal run lacks a saved base. The helper created the branch from
    # a full object ID; only that original branch creation can establish it.
    history = git(wt, "reflog", "show", "--format=%H %gs", "refs/heads/" + s["branch"]).splitlines()
    base = history[-1].split()[0] if history else ""
    if not base or history[-1] != f"{base} branch: Created from {base}":
        raise FactoryError("cannot establish the legacy slice base from its branch creation")
    git(wt, "merge-base", "--is-ancestor", base, head)
    dirty = bool(git(wt, "status", "--porcelain", "--untracked-files=all"))
    if dirty and not adopt_edits:
        raise FactoryError("legacy edits have no journal; inspect them, then pass --adopt-edits to include them")
    data, packet, p = plan(d, sid, profile or "mixed", continuing=True)
    if p["blockers"]:
        raise FactoryError("; ".join(p["blockers"]))
    rounds = [int(path.name[6:]) for path in prior[0].glob("round-*") if path.name[6:].isdigit()]
    n = max(rounds, default=1)
    if n > p["max_build_rounds"]:
        raise FactoryError("legacy attempt already exceeds the configured round budget")
    phase = "editing" if dirty or head == base else "checks"
    return Journal.create(d, data, packet, p, "local",
                          phase="recover-legacy" if s["status"] == "blocked" else phase,
                          resume_phase=phase, base=base, head=head, round=n)


def refresh_snapshot(d, j, mode):
    """Allow unrelated slices to progress while a run is stopped."""
    st = j.state
    if st["phase"] == "start":
        return
    prior = st["expected"]
    actual = d.load()
    sid = st["plan"]["slice"]
    s = slice_in(prior, sid)
    live = slice_in(actual, sid)
    if any(actual["criteria"].get(c) != prior["criteria"][c] for c in s["criteria"]):
        raise FactoryError("acceptance criteria changed since the run; reconcile the plan")
    for dep in s["depends_on"]:
        new = slice_in(actual, dep)
        if not eligible_predecessor(new):
            raise FactoryError(f"{dep}: dependency needs merge and verification before resuming")
        old = slice_in(prior, dep).get("merge_evidence")
        if old and new.get("merge_evidence") != old:
            raise FactoryError(f"{dep}: dependency merge changed since the run; reconcile the handoff")
    if actual["working_agreement"] != prior["working_agreement"]:
        if (st["phase"] not in {"local", "publish", "drafted", "ci", "ready"} or mode is None
                or not actual["working_agreement"].strip()):
            raise FactoryError("working agreement changed; reconcile authority before continuing")
    # Keep the original CAS target. A pending handoff may already be installed;
    # record() will accept either its exact before or exact after state.
    expected = dict(actual, slices=[s if row["id"] == sid else row for row in actual["slices"]])
    if live != s and st["phase"] not in {"handoff", "block", "attach", "attach-ready", "recover-legacy"}:
        raise FactoryError("delivery record changed during this run; reconcile the handoff")
    if expected != prior:
        j.save(st["phase"], expected=expected)


def record(d, j, operation, fields):
    """Reconcile both sides of a crash between tracked and local state writes."""
    st = j.state
    sid = st["plan"]["slice"]
    prior = st["expected"]
    updated = deepcopy(prior)
    slice_in(updated, sid).update(fields)
    actual = d.load()
    if actual != updated:
        if actual != prior:
            raise FactoryError("delivery record changed during this run; reconcile the handoff")
        run("sh", helper("spec-status"), d.project_map, d.spec, operation, sid,
            input_text=json.dumps(dict(fields, expected=prior, head=st["head"])))
    return updated


def retry_round(j, feedback, *, repair=None):
    n = j.state["round"]
    if n >= j.state["plan"]["max_build_rounds"]:
        raise FactoryError(f"build round limit reached. Outstanding feedback: {feedback}")
    j.save("editing" if repair else "build", round=n + 1, feedback=feedback, repair=repair,
           commit_message=j.state.get("commit_message") if repair == "commit" else None)


def repair_check_changes(j, wt, branch, head, feedback):
    ensure_head(wt, branch, head)
    changes = git(wt, "status", "--porcelain", "--untracked-files=all")
    if not changes:
        return False
    artifacts = set(j.state.get("check_artifacts", []))
    artifacts.update(filter(None, git(wt, "ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    j.save(j.state["phase"], check_artifacts=sorted(artifacts))
    dirty = (f"checks left changes in the worktree:\n{changes}\n"
             "Inspect these files and fix the cause so checks leave the candidate clean. "
             "Remove or ignore disposable output. If generated source or snapshots belong in the commit, "
             "list their exact paths in intended_files for independent review.")
    retry_round(j, "\n".join(filter(None, (feedback, dirty))), repair="checks")
    return True


def agent_directory(directory, role):
    # A resumed invocation must get a fresh response file.
    if (directory / (role + ".log")).exists():
        return Path(tempfile.mkdtemp(prefix=role + "-", dir=directory))
    return directory


def candidate_step(d, j, wt, branch):
    st = j.state
    phase, head, p = st["phase"], st["head"], st["plan"]
    n = st["round"]
    directory = j.path.parent / f"round-{n}"
    directory.mkdir(exist_ok=True)
    if phase in {"build", "editing"}:
        ensure_head(wt, branch, head, clean=phase == "build")
        context = json.dumps(st["packet"], indent=2)
        feedback = st["feedback"]
        if phase == "editing":
            feedback += "\nContinue from existing partial edits in this worktree. Inspect them before editing."
        if st.get("repair") == "commit":
            feedback += ("\nRepair the staged change or the proposed message using the hook diagnostics. "
                         "Return the full proposed commit message in summary, including any required trailers. "
                         "Leave Git operations to the runner and keep the repository hooks enabled.")
        j.save("editing")
        print(f"Round {n}: {p['roles']['builder']['agent']} building", flush=True)
        try:
            result = invoke("builder", p["roles"]["builder"], wt,
                            f"{BUILD}\n\n{context}\n\nPrevious feedback:\n{feedback}",
                            agent_directory(directory, "builder"), p["timeout_seconds"])
        except BuilderFeedback as exc:
            ensure_head(wt, branch, head)
            retry_round(j, str(exc), repair=st.get("repair") or "checks")
            return
        ensure_head(wt, branch, head)
        if result["outcome"] == "blocked":
            raise FactoryError(result["summary"])
        if st.get("check_artifacts"):
            candidates = set(git(wt, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0"))
            remaining = candidates.intersection(st["check_artifacts"]) - set(result["intended_files"])
            if remaining:
                retry_round(j, "Generated check files still eligible for staging. Remove, ignore, or explicitly "
                            "claim intentional source in intended_files:\n" +
                            "\n".join(sorted(remaining)), repair="checks")
                return
            j.save(j.state["phase"], check_artifacts=[])
        intended = sorted(set(st.get("intended_files", [])) | set(result["intended_files"]))
        j.save(j.state["phase"], intended_files=intended)
        if git(wt, "status", "--porcelain", "--untracked-files=all"):
            git(wt, "add", "-A")
            commit_message = st.get("commit_message")
            if st.get("repair") == "commit":
                proposed = directory / "commit-message.txt"
                log = directory / "trailers.log"
                with proposed.open("wb") as output:
                    rc = process(["git", "interpret-trailers", "--if-exists", "replace",
                                  "--trailer", f"Factory-Run: {j.path.parent.name}"], wt,
                                 result["summary"].strip() + "\n", log, p["timeout_seconds"], stdout=output)
                if rc:
                    retry_round(j, f"Could not format the repaired commit message: {tail(log)}", repair="commit")
                    return
                commit_message = proposed.read_text().strip()
            j.save("commit", tree=git(wt, "write-tree"), commit_action=f"factory-{j.path.parent.name}-round-{n}",
                   commit_message=commit_message)
        else:
            j.save("checks")
    elif phase == "commit":
        current = git(wt, "rev-parse", "HEAD")
        ensure_head(wt, branch, current)
        message = st.get("commit_message") or (
            f"{d.spec}: implement {p['slice']} (round {n})\n\nFactory-Run: {j.path.parent.name}")
        action = st.get("commit_action", f"factory-{j.path.parent.name}-round-{n}")
        if current == head:
            if (git(wt, "write-tree") != st["tree"] or git(wt, "diff", "--name-only")
                    or git(wt, "ls-files", "--others", "--exclude-standard")):
                raise FactoryError("staged candidate changed before commit; inspect the worktree")
            log = directory / "commit.log"
            print(f"Round {n}: committing the candidate (approve the signer if prompted)", flush=True)
            rc = process(["git", "-c", "core.logAllRefUpdates=true", "commit", "-F", "-"],
                         wt, message + "\n", log, p["timeout_seconds"], env=dict(os.environ, GIT_REFLOG_ACTION=action))
            current = git(wt, "rev-parse", "HEAD")
            if rc and current == head:
                ensure_head(wt, branch, head)
                # Git dies with 128 when it cannot create the signed commit
                # object. Hook rejection is an ordinary nonzero commit result.
                if rc == 128:
                    # A pre-commit hook may have formatted and staged files
                    # before the signer ran. Remember the index Git left us.
                    j.save("commit", tree=git(wt, "write-tree"))
                    raise AgentUnavailable(
                        f"Git could not create the commit. Check the signer or other fatal Git error "
                        f"below, then run factory resume {d.spec} --slice {p['slice']}. "
                        f"Round {n} is preserved.\n{tail(log, 1500)}")
                retry_round(j, f"git commit exited {rc}. Diagnostics from {log}:\n{tail(log, 1500)}\n"
                               f"Rejected message:\n{message}", repair="commit")
                return
        # Hooks may reformat staged files or rewrite the message. The reflog
        # identifies our branch update even after a crash before journal.save.
        entry = git(wt, "reflog", "show", "-1", "--format=%H %gs", "refs/heads/" + branch)
        ours = (entry.startswith(f"{current} {action}:") and
                git(wt, "rev-list", "-1", "--parents", current) == f"{current} {head}")
        # Older journals predate the per-round reflog marker.
        if not ours and "commit_action" not in st:
            identity = git(wt, "show", "-s", "--no-show-signature", "--format=%P%n%T%n%B", current)
            expected = f"{head}\n{st['tree']}\n{message}"
            ours = identity == expected or identity.startswith(expected + "\n")
        if not ours:
            raise ValueError("cannot identify the factory commit during recovery; inspect the slice branch")
        j.save("checks", head=current)
    elif phase == "checks":
        ensure_head(wt, branch, head, clean=True)
        if git(wt, "rev-parse", st["base"] + "^{tree}") == git(wt, "rev-parse", head + "^{tree}"):
            retry_round(j, "The slice has no changes relative to its starting commit. Implement the requested behavior.")
            return
        results, feedback = check_candidate(wt, head, p["checks"], directory, p["timeout_seconds"])
        if repair_check_changes(j, wt, branch, head, feedback):
            return
        reports = []
        consumer = slice_in(st["expected"], p["slice"])
        if not feedback and consumer.get("package_checks"):
            slices = package_sources(d, consumer, st["expected"])
            try:
                reports = package_reports(d, consumer, slices, head, directory, p["timeout_seconds"])
            except FactoryError as exc:
                feedback = str(exc)
            if repair_check_changes(j, wt, branch, head, feedback):
                return
        if feedback:
            retry_round(j, feedback)
        else:
            j.save("review", results=results, package_reports=reports)
    elif phase == "review":
        ensure_head(wt, branch, head, clean=True)
        diff = git(wt, "diff", "--no-ext-diff", "--no-textconv", st["base"], head, "--")
        changed = set(git(wt, "diff", "--name-only", "--no-renames", "--diff-filter=d", "-z",
                          st["base"], head, "--").split("\0"))
        intended = sorted(changed.intersection(st.get("intended_files", [])))
        j.save("review", intended_files=intended)
        review_input = dict(base=st["base"], candidate=head, diff=diff, check_results=st["results"],
                            intended_files=intended)
        if st.get("package_reports"):
            review_input["package_reports"] = st["package_reports"]
        print(f"Round {n}: {p['roles']['reviewer']['agent']} reviewing {head}", flush=True)
        result = invoke("reviewer", p["roles"]["reviewer"], wt,
                        REVIEW + "\n" + json.dumps(st["packet"]) + "\n" + json.dumps(review_input),
                        agent_directory(directory, "reviewer"), p["timeout_seconds"])
        ensure_head(wt, branch, head, clean=True)
        if result["outcome"] == "blocked":
            raise FactoryError(result["summary"])
        if result["outcome"] == "changes":
            retry_round(j, result["summary"])
        else:
            evidence = {c: {"commit": head, "criterion": p["criteria"][c], "commands": p["checks"]["criterion " + c],
                            "check": "Passed: " + ", ".join(map(shlex.join, p["checks"]["criterion " + c]))}
                        for c in p["criteria"]}
            note = f"Local checks passed. {p['roles']['reviewer']['agent']} approved: {result['summary']}"
            fields = dict(status="review", evidence=evidence, note=note)
            if st.get("package_reports"):
                fields["package_evidence"] = st["package_reports"]
            j.save("handoff", fields=fields)
    else:
        raise FactoryError(f"unknown factory stage {phase}")


def finish_review(d, j, wt):
    st = j.state
    sid = st["plan"]["slice"]
    s = slice_in(st["expected"], sid)
    head = st["head"]

    mode = st["pr_mode"]
    repo = d.repos[s["repo"]]
    phase = st["phase"]

    def validate():
        if d.load() != st["expected"]:
            raise FactoryError("delivery record changed before PR handoff")
        if not st["expected"]["working_agreement"].strip():
            raise FactoryError("record the authorized scope in the working agreement")
        ensure_head(wt, s["branch"], head, clean=True)
        if s["status"] != "review":
            raise FactoryError("PR handoff requires current evidence for every criterion")
        d.check_acceptance(s, st["expected"]["criteria"], head)

    def package_checks():
        if s.get("package_checks"):
            require_reports(s, package_sources(d, s, st["expected"], refresh=True), head)

    ensure_head(wt, s["branch"], head, clean=True)
    if phase in {"attach", "attach-ready"}:
        # A crash can leave either side of the tracked delivery write installed.
        fields = st["fields"]
        recorded = dict(s, pr=fields["pr"])
        pr = lookup(repo["url"], recorded)
        verify_pr(pr, recorded, repo["default"], head, draft=st.get("observed_draft", True))
        expected = record(d, j, "record-pr", fields)
        j.save("ready" if phase == "attach-ready" else "drafted", expected=expected)
        return False

    if mode == "local":
        if phase == "publish":
            j.save("local")
    elif phase in {"local", "publish"}:
        validate()
        package_checks()
        j.save("publish")
        pr = publish(d, s, wt, head, st["expected"]["criteria"], validate, ready=mode == "ready")
        label = "Draft PR" if pr["isDraft"] else "PR"
        fields = dict(pr=pr["number"], note=f"{s['note']}\n{label}: {pr['url']}")
        j.save("attach", fields=fields, observed_draft=pr["isDraft"])
        return False
    elif mode == "ready" and phase in {"drafted", "ci"}:
        validate()
        package_checks()
        j.save("ci")
        pr = promote(repo["url"], s, repo["default"], head, st["ready_checks"], st["ci_timeout"], validate)
        note = s["note"].removesuffix(f"\nDraft PR: {pr['url']}").removesuffix(f"\nPR: {pr['url']}")
        fields = dict(pr=pr["number"], note=f"{note}\nReady for your review: {pr['url']}")
        j.save("attach-ready", fields=fields, observed_draft=False)
        return False
    else:
        ready = phase == "ready"
        pr = lookup(repo["url"], s)
        verify_pr(pr, s, repo["default"], head, draft=not ready)
        print("Ready for your review:" if ready else "Draft PR:", pr["url"])
        if phase == "ci":
            j.save("drafted")
    expected = j.state["expected"]
    s = slice_in(expected, sid)
    print(f"Review handoff: {sid} at {head}\n{s['note']}")
    for c, item in s["evidence"].items():
        print(f"{c}: {item['check']}")
    remaining = [x["id"] for x in expected["slices"] if x["id"] != sid and x["status"] != "verified"]
    print("Other outstanding slices:", ", ".join(remaining) or "none")
    return True


def continue_slice(d, j):
    p = j.state["plan"]
    sid, repo = p["slice"], p["repository"]
    if j.state["repositories"] != d.repos:
        raise FactoryError("selected repository or base changed since this run")
    _, wt = d.registered_worktree(repo)
    print("Run files:", j.path.parent, flush=True)
    if j.state["phase"] == "start":
        started = json.loads(run("sh", helper("start-slice"), d.project_map, d.spec, sid,
                                 "--expect-record-stdin", "--json", "--factory-attempt", j.path.parent.name,
                                 input_text=json.dumps(j.state["expected"])))
        packet = dict(j.state["packet"], repository_context=context_files(d, repo))
        j.save("build", expected=started["delivery"], head=started["base"], base=started["base"], packet=packet)
    while True:
        st = j.state
        phase = st["phase"]
        s = slice_in(st["expected"], sid)
        if phase == "recover-legacy":
            expected = record(d, j, "recover-interrupt", {"status": "implementing"})
            j.save(st["resume_phase"], expected=expected)
            continue
        if phase in {"handoff", "block"}:
            expected = record(d, j, "local-handoff", st["fields"])
            j.save("local" if phase == "handoff" else "blocked", expected=expected)
            continue
        if phase not in {"attach", "attach-ready"} and d.load() != st["expected"]:
            raise FactoryError("delivery record changed during this run; reconcile the handoff")
        if phase == "blocked":
            raise FactoryError(s["note"])
        if phase in {"local", "publish", "attach", "drafted", "ci", "attach-ready", "ready"}:
            if finish_review(d, j, wt):
                return
            continue
        try:
            candidate_step(d, j, wt, s["branch"])
        except FactoryError as exc:
            # Logical failures retain the existing blocked handoff. Interruptions
            # and transient infrastructure failures leave the active checkpoint.
            if isinstance(exc, AgentUnavailable):
                raise
            ensure_head(wt, s["branch"], j.state["head"])
            note = f"{str(exc)[:2000]}\nInspect {j.path.parent.relative_to(d.directory)} and the slice worktree."
            j.save("block", fields=dict(status="blocked", note=note, evidence={}))


def status(d, sid, remote, as_json):
    report = json.loads(run("sh", helper("spec-status"), d.project_map, d.spec, "status", "--json"))
    records = {s["id"]: s for s in d.load()["slices"]}
    if remote:
        report["freshness"] = "GitHub lookup requested; local refs not fetched"
    if sid:
        report["slices"] = [s for s in report["slices"] if s["id"] == sid]
        if not report["slices"]:
            raise FactoryError(f"unknown slice {sid}")
    for s in report["slices"]:
        for key in ("merge_evidence", "package_evidence"):
            if key in records[s["id"]]:
                s[key] = records[s["id"]][key]
        j = Journal.for_slice(d, s["id"])
        if j:
            s["factory"] = {k: j.state.get(k) for k in ("phase", "round", "head", "pr_mode")}
            s["factory"]["draft"] = j.state["pr_mode"] != "local"
        if remote and s.get("branch"):
            try:
                pr = lookup(d.repos[s["repo"]]["url"], s)
                s["remote_pr"] = pr
                if pr:
                    ref, _ = d.paths(s["repo"])
                    if (pr["isCrossRepository"] or pr["headRefName"] != s["branch"]
                            or pr["baseRefName"] != d.repos[s["repo"]]["default"]
                            or pr["headRefOid"] != git(ref, "rev-parse", "refs/heads/" + s["branch"])):
                        s["warning"] = "PR repository, branch, base or commit differs from the local slice"
            except (OSError, ValueError) as exc:
                s["warning"] = f"remote state unverified: {exc}"
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for s in report["slices"]:
            progress = s.get("factory") or {}
            print(f"{s['id']}: {s['status']} | factory: {progress.get('phase', 'no journal')} | "
                  f"round: {progress.get('round', '-')} | commit: {progress.get('head') or '-'}")
            if s.get("note"):
                print(s["note"])
            if remote:
                pr = s.get("remote_pr")
                print("PR:", f"{pr['url']} ({pr['state']})" if pr else "none confirmed")
                if s.get("warning"):
                    print(s["warning"])
        print(f"Spec {d.spec}: {report['completion']} ({report['freshness']})")
        for gap in report["acceptance_gaps"]:
            print("Acceptance:", gap)


def handoff_options(d, preview, mode):
    if mode == "draft":
        preview["handoff"] = "Push the reviewed commit and open or reuse its draft PR."
    if mode != "ready":
        return {}
    cfg = json.loads((d.root / "factory/config.json").read_text())
    repo = preview["repository"]
    by_repo = cfg.get("ready_checks", {})
    gates = by_repo.get(repo) if isinstance(by_repo, dict) else None
    if not isinstance(gates, list) or not gates or not all(isinstance(g, str) and g.strip() for g in gates):
        raise FactoryError(f"configure the CI checks for {repo} under ready_checks in factory/config.json")
    preview["handoff"] = f"Push the reviewed commit, wait for {', '.join(gates)}, and mark the PR ready for review."
    return dict(ready_checks=gates, ci_timeout=cfg["timeout_seconds"])


def start_planned(d, data, packet, preview, mode, options):
    for role in preview["roles"].values():
        if not shutil.which(role["agent"]):
            raise FactoryError(f"install {role['agent']} or select another profile")
    journal = Journal.create(d, data, packet, preview, mode or "local", **options)
    continue_slice(d, journal)


def run_spec(d, profile, mode):
    while True:
        report = reconcile(d)
        ready = set(report["eligible_predecessors"])
        data = d.load()
        if not data["slices"]:
            raise FactoryError("populate delivery.json with criteria and planned slices first")
        busy = {s["repo"] for s in data["slices"] if s.get("branch") and s["id"] not in ready}
        for s in data["slices"]:
            if s["status"] != "planned" or s["repo"] in busy or not ready.issuperset(s["depends_on"]):
                continue
            if Journal.for_slice(d, s["id"]):
                report["issues"][s["id"]] = "interrupted start; use factory resume"
                continue
            planned, packet, preview = plan(d, s["id"], profile)
            if planned != data:
                raise FactoryError("delivery record changed during scheduling; retry the run")
            if preview["blockers"]:
                report["issues"][s["id"]] = "; ".join(preview["blockers"])
                continue
            options = handoff_options(d, preview, mode)
            print_plan(preview)
            try:
                start_planned(d, planned, packet, preview, mode, options)
            except FactoryError:
                if slice_in(d.load(), s["id"])["status"] != "blocked":
                    raise
            break
        else:
            show_verification(report)
            pending = len(report["verified_slices"]) < report["total_slices"]
            return 1 if report["issues"] or (not pending and not report["verified"]) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "resume", "status", "verify"):
        cmd = sub.add_parser(name)
        cmd.add_argument("spec")
        if name != "verify":
            cmd.add_argument("--slice")
        if name in {"plan", "run"}:
            cmd.add_argument("--profile", default="mixed")
        if name in {"plan", "run", "resume"}:
            mode = cmd.add_mutually_exclusive_group()
            mode.add_argument("--draft-pr", action="store_const", const="draft", dest="mode",
                              help="authorize pushing the reviewed branch and opening or reusing its draft PR")
            mode.add_argument("--ready-pr", action="store_const", const="ready", dest="mode",
                              help="push the reviewed branch and mark its PR ready after CI passes")
            mode.add_argument("--local-only", action="store_const", const="local", dest="mode",
                              help="use a local handoff, including on resumed runs")
        if name in {"plan", "status", "verify"}:
            cmd.add_argument("--json", action="store_true")
        if name == "status":
            cmd.add_argument("--remote", action="store_true")
        if name == "resume":
            cmd.add_argument("--profile", help="profile for a pre-journal attempt")
            cmd.add_argument("--adopt-edits", action="store_true",
                             help="include existing edits when recovering a pre-journal run")
    args = parser.parse_args()
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        d = Delivery("project-repositories.yaml", args.spec)
        if args.command == "status":
            status(d, args.slice, args.remote, args.json)
            return 0
        if args.command == "verify" or (args.command == "run" and not args.slice):
            root = run_root(d)
            root.mkdir(exist_ok=True)
            with exclusive(root):
                if args.command == "run":
                    return run_spec(d, args.profile, args.mode)
                report = reconcile(d)
                if args.json:
                    print(json.dumps(report, indent=2))
                else:
                    show_verification(report)
                return 0 if report["verified"] else 1
        if args.command in {"plan", "run"}:
            data, packet, preview = plan(d, args.slice, args.profile)
            options = handoff_options(d, preview, args.mode)
            if args.command == "plan" and args.json:
                print(json.dumps(preview, indent=2))
            else:
                print_plan(preview)
            if args.command == "plan":
                return 0
            if preview["blockers"]:
                raise FactoryError("resolve the preview blockers before running")
        root = run_root(d)
        root.mkdir(exist_ok=True)
        with exclusive(root):
            if args.command == "resume":
                journal = Journal.find(d, args.slice)
                if journal is None:
                    journal = adopt_legacy(d, args.slice, args.adopt_edits, args.profile)
                elif args.profile and args.profile != journal.state["plan"].get("profile"):
                    raise FactoryError("a journalled run uses its saved profile")
                if args.mode == "local":
                    journal.save(journal.state["phase"], pr_mode="local")
                refresh_snapshot(d, journal, args.mode)
                if args.mode in {"draft", "ready"}:
                    options = handoff_options(d, dict(journal.state["plan"]), args.mode)
                    journal.save(journal.state["phase"], pr_mode=args.mode, **options)
                continue_slice(d, journal)
            else:
                start_planned(d, data, packet, preview, args.mode, options)
        return 0
    except KeyboardInterrupt:
        print("Factory interrupted. Use factory resume to continue from the saved stage.", file=sys.stderr)
        return 130
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        print(f"factory: {exc}", file=sys.stderr)
        return 1
