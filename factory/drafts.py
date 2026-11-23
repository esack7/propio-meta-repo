"""Publish exactly the reviewed slice branch and reconcile its GitHub PR."""

import json
import tempfile
import time
from urllib.parse import urlsplit

from agents import FactoryError
from delivery import git, run

FIELDS = "id,number,url,state,isDraft,isCrossRepository,headRefName,headRefOid,baseRefName"


def lookup(target, s, for_publish=False, checks=False):
    fields = FIELDS + ",statusCheckRollup" if checks else FIELDS
    args = ["--repo", target, "--json", fields]
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


def verify_pr(pr, s, base, head=None, *, draft=True):
    if (not pr or pr["state"] != "OPEN" or pr["isCrossRepository"]
            or (draft is not None and pr["isDraft"] != draft)
            or pr["headRefName"] != s["branch"] or pr["baseRefName"] != base
            or (s.get("pr") and pr["number"] != s["pr"])):
        raise FactoryError("existing PR does not match this repository, draft state, head branch and base")
    if head is not None and pr["headRefOid"] != head:
        raise FactoryError("PR has not been confirmed at the reviewed commit; inspect GitHub")


def publish(d, s, wt, head, criteria, validate, *, ready=False):
    """Re-query before every retry, including after an ambiguous create result."""
    # gh accepts the canonical GitHub clone URL as an explicit --repo target.
    target = d.repos[s["repo"]]["url"]
    base = d.repos[s["repo"]]["default"]
    branch = s["branch"]
    remote_ref = "refs/heads/" + branch
    pr = lookup(target, s, for_publish=True)

    if pr:
        verify_pr(pr, s, base, draft=None if ready else True)
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
        title = s.get("pr_title", f"feat({d.spec}): implement {s['id'].replace('-', ' ')}")
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as description:
                description.write("\n".join(body) + "\n")
                description.flush()
                run("gh", "pr", "create", "--repo", target, "--draft", "--head", branch,
                    "--base", base, "--title", title, "--body-file", description.name)
        except ValueError:
            # GitHub may have created the draft even when the response was lost.
            pr = lookup(target, s, for_publish=True)
            if pr is None:
                raise
        else:
            pr = lookup(target, s, for_publish=True)
    verify_pr(pr, s, base, head, draft=None if ready else True)
    validate()
    return pr


class ChecksIncomplete(FactoryError):
    """A CI gate needs attention before this PR can be handed back ready."""


def pending_checks(pr, gates):
    """Evaluate matching reports on the reviewed head together."""
    states = {gate: set() for gate in gates}
    for check in pr["statusCheckRollup"]:
        if check.get("__typename") == "StatusContext":
            name, state = check["context"], check["state"]
        else:
            workflow = check.get("workflowName")
            name = f"{workflow} / {check['name']}" if workflow else check["name"]
            state = check["conclusion"] if check["status"] == "COMPLETED" else "PENDING"
        if name in states:
            states[name].add(state)
    pending = []
    failures = []
    for gate, reports in states.items():
        if "SUCCESS" in reports:
            continue
        if not reports or reports.intersection({"PENDING", "EXPECTED"}):
            pending.append(gate)
        else:
            failures.append(f"{gate} reported {', '.join(sorted(reports))}")
    if failures:
        details = "; ".join(failures)
        raise ChecksIncomplete(f"{pr['url']}: {details}. Repair or rerun CI, then resume.")
    return pending


def promote(target, s, base, head, gates, timeout, validate):
    deadline = time.monotonic() + timeout
    while True:
        pr = lookup(target, s, checks=True)
        verify_pr(pr, s, base, head, draft=None)
        pending = pending_checks(pr, gates)
        if not pending:
            validate()
            # Refresh the remote head and CI after local validation, immediately before promotion.
            pr = lookup(target, s, checks=True)
            verify_pr(pr, s, base, head, draft=None)
            pending = pending_checks(pr, gates)
            if not pending:
                break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ChecksIncomplete(f"{pr['url']}: still waiting for {', '.join(pending)}. Resume to check again.")
        print(f"Waiting for {', '.join(pending)} on {pr['url']}", flush=True)
        time.sleep(min(10, remaining))

    if not pr["isDraft"]:
        return pr
    run("gh", "pr", "ready", pr["number"], "--repo", target)
    for attempt in range(3):
        if attempt:
            time.sleep(1)
        confirmed = lookup(target, s)
        verify_pr(confirmed, s, base, head, draft=None)
        if not confirmed["isDraft"]:
            return confirmed
    raise FactoryError(f"{pr['url']}: GitHub still reports a draft after promotion. Resume to confirm.")


PR_COMMENTS = """query($id: ID!, $endCursor: String) {
  node(id: $id) {
    ... on PullRequest {
      comments(first: 100, after: $endCursor) {
        nodes { body viewerDidAuthor url }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}"""


def post_review_comment(target, s, base, head, pr, reviewer, rationale, validate):
    marker = f"<!-- factory-review:{head} -->"
    body = (f"**Automated factory review** · {reviewer}\n\n"
            f"I recommend merging the reviewed commit `{head}`.\n\n{rationale}\n\n{marker}")
    # GitHub can accept a comment before the runner saves its receipt.
    pages = json.loads(run("gh", "api", "graphql", "--hostname", urlsplit(pr["url"]).hostname,
                           "--paginate", "--slurp", "-f", f"query={PR_COMMENTS}", "-f", f"id={pr['id']}"))
    for page in pages:
        for comment in page["data"]["node"]["comments"]["nodes"]:
            if comment["viewerDidAuthor"] and comment["body"].rstrip().endswith(marker):
                return comment["url"]
    validate()
    verify_pr(lookup(target, s), s, base, head, draft=False)
    return run("gh", "pr", "comment", s["pr"], "--repo", target,
               "--body-file", "-", input_text=body)
