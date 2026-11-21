"""Reconcile a whole spec against fetched Git history and exact package inputs."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

from agents import FactoryError, process, tail
from delivery import AwaitingMerge, SHARED, atomic_json, exclusive, git
from journal import run_root
from package_evidence import gates, inputs, passed


def fetch_base(d, repo):
    ref, _ = d.paths(repo)
    base = d.repos[repo]["default"]
    try:
        git(ref, "fetch", "--no-tags", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}")
    except ValueError as exc:
        raise FactoryError(f"could not fetch the configured default branch: {exc}") from exc


def package_sources(d, consumer, delivery, refresh=False):
    slices = {s["id"]: s for s in delivery["slices"]}
    producers = {producer for producer, _, _ in gates(consumer, slices)}
    if refresh:
        for repo in sorted({slices[p]["repo"] for p in producers}):
            fetch_base(d, repo)
    for producer in sorted(producers):
        source = slices[producer]
        proof = d.confirm_merge(source, require_pr=True)
        slices[producer] = dict(source, merge_evidence=proof)
    return slices


def package_reports(d, consumer, slices, commit, directory, timeout, cached=()):
    """Reuse a passing report only for the same mode, scripts and both commits."""
    reports = []
    for expected in inputs(consumer, slices, commit):
        match = next((r for r in cached if passed(r, expected)), None)
        if match:
            reports.append(match)
            continue
        attempt = Path(tempfile.mkdtemp(prefix="package-", dir=directory))
        output = attempt / "result.json"
        log = attempt / "check.log"
        command = [sys.executable, SHARED.parent / "verify-packages/scripts/verify-packages.py",
                   d.project_map, d.spec, expected["producer"], expected["consumer"],
                   "--producer-commit", expected["producer_commit"], "--consumer-commit", commit,
                   "--mode", expected["mode"], "--report", output]
        for check in expected["checks"]:
            command.extend(["--check", check])
        rc = process(command, d.root, "", log, timeout)
        if rc:
            raise FactoryError(f"{expected['mode']} package check failed for {expected['producer']} → "
                               f"{expected['consumer']} (see {log}): {tail(log, 1500)}")
        report = json.loads(output.read_text())
        if not passed(report, expected):
            raise FactoryError(f"package report does not match the requested inputs: {output}")
        reports.append(report)
    return reports


def reconcile(d):
    original = d.load()
    data = deepcopy(original)
    slices = {s["id"]: s for s in data["slices"]}
    checked, waiting, issues = [], {}, {}
    fetched = {}
    for sid, s in slices.items():
        prior_status = s["status"]
        missing = [dep for dep in s["depends_on"] if dep not in checked]
        dependency_wait = "awaiting verified dependencies: " + ", ".join(missing)
        if s["status"] not in {"review", "merged", "verified"}:
            if s["status"] == "blocked":
                issues[sid] = s["note"]
            elif s["status"] == "implementing":
                waiting[sid] = "implementation in progress; use factory resume for an interrupted run"
            elif missing:
                waiting[sid] = dependency_wait
            continue
        repo = s["repo"]
        try:
            if repo not in fetched:
                try:
                    fetch_base(d, repo)
                    fetched[repo] = None
                except (OSError, ValueError) as exc:
                    fetched[repo] = str(exc)
            if fetched[repo]:
                raise FactoryError(fetched[repo])
            proof = d.merged(s, require_pr=True)
            s.update(status="merged", merge_evidence=proof)
            d.check_acceptance(s, data["criteria"], proof["head"])
            if missing:
                waiting[sid] = dependency_wait
                continue
            if s.get("package_checks"):
                timeout = json.loads((d.root / "factory/config.json").read_text())["timeout_seconds"]
                if type(timeout) is not int or timeout <= 0:
                    raise FactoryError("timeout_seconds must be a positive integer")
                reports = package_reports(d, s, slices, proof["commit"], run_root(d), timeout,
                                          s.get("package_evidence", []))
                s["package_evidence"] = reports
            else:
                s.pop("package_evidence", None)
            s["status"] = "verified"
            checked.append(sid)
        except AwaitingMerge as exc:
            if prior_status in {"merged", "verified"}:
                issues[sid] = f"recorded merge no longer confirmed: {exc}"
            else:
                waiting[sid] = str(exc)
        except (OSError, ValueError) as exc:
            issues[sid] = str(exc)

    with exclusive(d.directory):
        if (d.directory / ".delivery.lock").exists() or d.load() != original:
            raise FactoryError("delivery record changed or is locked; retry verification")
        for sid in checked:
            s = slices[sid]
            ref, _ = d.paths(s["repo"])
            if git(ref, "rev-parse", "refs/heads/" + s["branch"]) != s["merge_evidence"]["head"]:
                raise FactoryError(f"{sid}: head changed during verification; retry")
        d.validate(data)
        gaps = d.completion_errors(data)
        if data != original:
            atomic_json(d.path, data)
    return {"spec": d.spec, "verified": bool(slices) and len(checked) == len(slices) and not gaps,
            "verified_slices": checked, "total_slices": len(slices), "waiting": waiting,
            "issues": issues, "acceptance_gaps": gaps,
            "evidence": {sid: {"merge": slices[sid]["merge_evidence"], "criteria": slices[sid]["evidence"],
                               "packages": slices[sid].get("package_evidence", [])} for sid in checked},
            "criteria": {c: [sid for sid in checked if c in slices[sid]["criteria"]] for c in data["criteria"]}}


def show_verification(report):
    count = len(report["verified_slices"])
    state = "VERIFIED" if report["verified"] else "incomplete"
    print(f"Spec {report['spec']}: {state} ({count}/{report['total_slices']} slices verified)")
    for category in ("waiting", "issues"):
        for sid, reason in report[category].items():
            print(f"{sid}: {reason}")
    for gap in report["acceptance_gaps"]:
        print("Acceptance:", gap)
    if report["verified"]:
        for criterion, covered in report["criteria"].items():
            print(f"{criterion}: verified by {', '.join(covered)}")
