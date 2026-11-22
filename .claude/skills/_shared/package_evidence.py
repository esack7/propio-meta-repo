"""Package gates declared on a consumer slice and bound to exact delivered commits."""

import re


def gates(consumer, slices):
    requirements = consumer.get("package_checks", [])
    if not isinstance(requirements, list):
        raise ValueError("package_checks must be a list")
    seen = set()
    for item in requirements:
        if not isinstance(item, dict) or item.keys() - {"producer_slice", "mode", "checks"}:
            raise ValueError("package_checks entries require producer_slice, checks and an optional mode")
        producer = item.get("producer_slice")
        mode = item.get("mode", "candidate")
        checks = item.get("checks")
        if (not isinstance(producer, str) or producer not in consumer["depends_on"] or slices[producer]["repo"] == consumer["repo"]
                or mode not in ("candidate", "published") or (producer, mode) in seen):
            raise ValueError("package check needs a distinct dependency repository and unique producer/mode")
        if not isinstance(checks, list) or not checks or not all(
            isinstance(c, str) and c.strip() and not c.startswith("-") and "\0" not in c for c in checks
        ):
            raise ValueError("package checks require consumer npm script names")
        seen.add((producer, mode))
        yield producer, mode, checks


def inputs(consumer, slices, consumer_commit):
    for producer, mode, checks in gates(consumer, slices):
        source = slices[producer]
        commit = source.get("merge_evidence", {}).get("commit")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"{producer}: verify the producer merge before checking packages")
        yield dict(mode=mode, producer=source["repo"], producer_commit=commit,
                   consumer=consumer["repo"], consumer_commit=consumer_commit, checks=checks)


def passed(report, expected):
    return (isinstance(report, dict) and report.get("passed") is True
            and all(report.get(k) == v for k, v in expected.items())
            and all(isinstance(report.get(k), str) and report[k] for k in ("package", "installed_version", "node", "npm"))
            and (expected["mode"] != "candidate" or
                 (isinstance(report.get("artifact_sha256"), str) and
                  bool(re.fullmatch(r"[0-9a-f]{64}", report["artifact_sha256"])))))


def require_reports(consumer, slices, commit=None):
    if not consumer.get("package_checks"):
        return
    commit = commit or consumer.get("merge_evidence", {}).get("commit")
    if not commit:
        raise ValueError("missing consumer merge evidence for package checks")
    for expected in inputs(consumer, slices, commit):
        if not any(passed(r, expected) for r in consumer.get("package_evidence", [])):
            raise ValueError(f"missing current {expected['mode']} package evidence for {expected['producer']}")
