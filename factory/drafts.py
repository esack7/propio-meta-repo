"""Publish exactly the reviewed slice branch and reconcile its GitHub draft."""

import json
import tempfile

from agents import FactoryError
from delivery import git, run

FIELDS = "number,url,state,isDraft,isCrossRepository,headRefName,headRefOid,baseRefName"


def lookup(target, s, for_publish=False):
    args = ["--repo", target, "--json", FIELDS]
    if s.get("pr"):
        try:
            pr = json.loads(run("gh", "pr", "view", s["pr"], *args))
            if not isinstance(pr, dict) or pr.get("number") != s["pr"]:
                raise ValueError("GitHub did not return the recorded PR")
            return pr
        except ValueError as exc:
            raise FactoryError(f"Cannot read recorded PR #{s['pr']} in {target}: {exc}") from exc
    rows = json.loads(run("gh", "pr", "list", "--head", s["branch"], "--state", "all", *args))
    matches = [r for r in rows if r["headRefName"] == s["branch"] and not r["isCrossRepository"]]
    open_matches = [r for r in matches if r["state"] == "OPEN"]
    if len(open_matches) == 1:
        return open_matches[0]
    if for_publish:
        matches = [r for r in matches if r["state"] != "CLOSED"]
        if any(r["state"] == "MERGED" for r in matches) and not open_matches:
            raise FactoryError("a PR for this branch already merged; reconcile its delivery record")
    if len(matches) > 1:
        raise FactoryError("multiple PRs use this branch; reconcile the delivery record")
    return next(iter(matches), None)


def verify_draft(pr, s, base, head=None):
    if (not pr or pr["state"] != "OPEN" or not pr["isDraft"] or pr["isCrossRepository"]
            or pr["headRefName"] != s["branch"] or pr["baseRefName"] != base
            or (s.get("pr") and pr["number"] != s["pr"])):
        raise FactoryError("existing PR does not match this repository, draft, head branch and base")
    if head is not None and pr["headRefOid"] != head:
        raise FactoryError("draft PR has not been confirmed at the reviewed commit; inspect GitHub")


def publish(d, s, wt, head, criteria, validate):
    """Re-query before every retry, including after an ambiguous create result."""
    # gh accepts the canonical GitHub clone URL as an explicit --repo target.
    target = d.repos[s["repo"]]["url"]
    base = d.repos[s["repo"]]["default"]
    branch = s["branch"]
    remote_ref = "refs/heads/" + branch
    pr = lookup(target, s, for_publish=True)

    if pr:
        verify_draft(pr, s, base)
    validate()
    if git(wt, "remote", "get-url", "--push", "--all", "origin").splitlines() != [target]:
        raise FactoryError("origin push destination differs from the selected repository")
    remote = git(wt, "ls-remote", "--heads", "origin", remote_ref)
    previous = remote.split()[0] if remote else ""
    if pr and pr["headRefOid"] != previous:
        raise FactoryError("PR and remote branch disagree about the head; inspect GitHub")
    if previous != head:
        if previous:
            try:
                git(wt, "merge-base", "--is-ancestor", previous, head)
            except ValueError as exc:
                raise FactoryError("remote branch has an unexpected commit; refusing to overwrite it") from exc
        validate()
        # Only create or fast-forward. The lease protects the ancestry check against a racing push.
        git(wt, "push", "--no-follow-tags", "--recurse-submodules=no",
            f"--force-with-lease={remote_ref}:{previous}", "origin", f"{head}:{remote_ref}")
        if pr:
            pr = lookup(target, dict(s, pr=pr["number"]))
            if pr is None:
                raise FactoryError("draft PR disappeared after branch update; inspect GitHub")
    if pr is None:
        validate()
        body = [f"Implements slice `{s['id']}` of spec `{d.spec}`.", "", f"Reviewed commit: `{head}`", ""]
        body.extend(f"- {criteria[c]}\n  {s['evidence'][c]['check']}" for c in s["criteria"])
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as description:
                description.write("\n".join(body) + "\n")
                description.flush()
                run("gh", "pr", "create", "--repo", target, "--draft", "--head", branch,
                    "--base", base, "--title", f"{d.spec}: {s['id']}", "--body-file", description.name)
        except ValueError:
            # GitHub may have created the draft even when the response was lost.
            pr = lookup(target, s, for_publish=True)
            if pr is None:
                raise
        else:
            pr = lookup(target, s, for_publish=True)
    verify_draft(pr, s, base, head)
    validate()
    return pr
