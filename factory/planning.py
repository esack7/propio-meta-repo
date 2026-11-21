"""Assemble an inspectable run from the authoritative spec and project map."""

import json
from pathlib import Path
import shlex

from agents import FactoryError, role_config
from delivery import SHARED, eligible_predecessor, run


def helper(name):
    return SHARED.parent / name / "scripts" / (name + ".sh")


def read_file(root, name):
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root):
        raise FactoryError(f"context path outside {root}: {name}")
    return path.read_text()


def context_files(d, target, blockers=None):
    # The existing shell helper owns Git-critical fields. Normal YAML is valid
    # for context, including quoted paths and inline arrays.
    query = ('map = YAML.safe_load(File.read(ARGV[0]), aliases: true); '
             'puts JSON.generate(map.fetch("repositories").map { |r| '
             '[r.fetch("name"), r.fetch("context", [])] }.to_h)')
    contexts = json.loads(run("ruby", "-ryaml", "-rjson", "-e", query, d.project_map))
    contents = {}
    for name in d.repos:
        if blockers is not None and not (d.root / "repos" / name).exists():
            blockers.append(f"set up the {name} reference clone with setup-repositories")
            continue
        ref, wt = d.paths(name)
        directory = wt if name == target and wt.is_dir() else ref
        entries = contexts[name]
        if not isinstance(entries, list) or not all(isinstance(p, str) and p for p in entries):
            raise FactoryError(f"{name}: context must be an ordered list of paths")
        for path in entries:
            try:
                contents[str(directory / path)] = read_file(directory, path)
            except FileNotFoundError:
                if blockers is None:
                    raise
                blockers.append(f"missing configured context: {directory / path}")
    return contents


def commands(value, label):
    if not isinstance(value, list) or not all(
        isinstance(argv, list) and argv and all(isinstance(a, str) and a and "\0" not in a for a in argv)
        for argv in value
    ):
        raise FactoryError(f"{label} must be an array of command argument arrays")
    return value


def config_for(d, profile):
    cfg = json.loads((d.root / "factory/config.json").read_text())
    profiles = cfg["profiles"]
    if profile not in profiles:
        raise FactoryError(f"unknown profile {profile!r}; choices: {', '.join(profiles)}")
    if not isinstance(cfg["repo_checks"], dict):
        raise FactoryError("repo_checks must map repository names to command arrays")
    roles = profiles[profile]
    if set(roles) != {"builder", "reviewer"}:
        raise FactoryError("profile requires a builder and a reviewer")
    for key in ("max_build_rounds", "timeout_seconds"):
        if type(cfg[key]) is not int or cfg[key] < 1:
            raise FactoryError(f"{key} must be a positive integer")
    return cfg, {role: role_config(value) for role, value in roles.items()}


def plan(d, sid, profile, continuing=False):
    data = d.load()
    if not data["slices"]:
        raise FactoryError("populate delivery.json with criteria and planned slices first")
    if not sid:
        planned = [s for s in data["slices"] if s["status"] == "planned"]
        merged = {s["id"] for s in data["slices"] if eligible_predecessor(s)}
        busy = {s["repo"] for s in data["slices"] if s.get("branch") and s["id"] not in merged}
        ready = [s for s in planned if s["repo"] not in busy and merged.issuperset(s["depends_on"])]
        sid = (ready or planned)[0]["id"] if planned else None
    s = next((s for s in data["slices"] if s["id"] == sid), None)
    if not s:
        raise FactoryError("no matching planned slice; select a slice with --slice")
    cfg, roles = config_for(d, profile)
    repo = s["repo"]
    report = json.loads(run("sh", helper("spec-status"), d.project_map, d.spec, "status", "--json"))
    row = next(r for r in report["repositories"] if r["repo"] == repo)
    blockers = []
    if not continuing and (s["status"] != "planned" or s.get("branch")):
        blockers.append(f"{sid} is already {s['status']}; run requires a new planned slice")
    if not data["working_agreement"].strip():
        blockers.append("record the authorized work in working_agreement")
    if row.get("warning"):
        blockers.append(row["warning"])
    if row.get("worktree") != "present":
        blockers.append("prepare the spec using prepare-spec")
    if row.get("dirty") and not continuing:
        blockers.append("the selected worktree has local changes")
    for other in data["slices"]:
        prior = other.get("branch") and other["branch"] == row.get("branch") and other["repo"] == repo
        if other["id"] == sid or not (prior or other["id"] in s["depends_on"]):
            continue
        if not eligible_predecessor(other):
            action = "be verified" if other["status"] == "merged" else "merge"
            blockers.append(f"{other['id']} must {action} first (currently {other['status']})")
        elif other["status"] == "verified":
            blockers.extend(gap for gap in report["acceptance_gaps"] if gap.startswith(other["id"] + ":"))
    required = cfg["repo_checks"].get(repo)
    if required is None:
        blockers.append(f"configure repo_checks for {repo} in factory/config.json")
    checks = {"repository": commands([] if required is None else required, "repo_checks")}
    specific = s.get("factory_checks", {})
    if not isinstance(specific, dict) or specific.keys() - set(s["criteria"]):
        raise FactoryError("factory_checks must map assigned criterion IDs to checks")
    for c in s["criteria"]:
        checks["criterion " + c] = commands(specific.get(c, []), c)
        if not checks["criterion " + c]:
            blockers.append(f"add a criterion check in factory_checks.{c}")
    docs = {name: read_file(d.directory, name) for name in ("requirements.md", "design.md", "tasks.md")}
    repo_context = context_files(d, repo, blockers)
    packet = {"spec": d.spec, "slice": sid, "repository": repo, "slice_note": s.get("note", ""),
              "working_agreement": data["working_agreement"],
              "criteria": {c: data["criteria"][c] for c in s["criteria"]},
              "documents": docs, "repository_context": repo_context, "checks": checks,
              "package_checks": s.get("package_checks", [])}
    preview = {"spec": d.spec, "slice": sid, "repository": repo,
               "worktree": str(d.directory / "repos" / repo), "depends_on": s["depends_on"],
               "profile": profile, "roles": roles, "criteria": packet["criteria"],
               "working_agreement": data["working_agreement"],
               "documents": list(docs), "repository_context": list(repo_context),
               "checks": checks, "package_checks": packet["package_checks"], "max_build_rounds": cfg["max_build_rounds"],
               "timeout_seconds": cfg["timeout_seconds"], "blockers": blockers,
               "handoff": "Local commit, check evidence, independent review. Inspect the branch for PR preparation."}
    return data, packet, preview


def print_plan(p):
    print(f"{p['spec']} / {p['slice']} in {p['repository']}\nWorktree: {p['worktree']}")
    print("Dependencies:", ", ".join(p["depends_on"]) or "none")
    print("Working agreement:", p["working_agreement"] or "(missing)")
    for role, cfg in p["roles"].items():
        print(f"{role.capitalize()}: {cfg['agent']}" + (f" ({cfg['model']})" if "model" in cfg else ""))
    for c, description in p["criteria"].items():
        print(f"Criterion {c}: {description}")
    print("Context:", *p["documents"], *p["repository_context"], sep="\n  ")
    for label, checks in p["checks"].items():
        for argv in checks:
            print(f"Check ({label}): {shlex.join(argv)}")
    for reason in p["blockers"]:
        print("Blocked:", reason)
    for gate in p["package_checks"]:
        print(f"Package ({gate.get('mode', 'candidate')}): {gate['producer_slice']} → {p['slice']}, "
              f"scripts: {', '.join(gate['checks'])}")
    print(f"Limit: {p['max_build_rounds']} build rounds, {p['timeout_seconds']}s per command")
    print("Handoff:", p["handoff"])
    print("Start-slice verifies current remote dependencies and branch eligibility at run time.")
