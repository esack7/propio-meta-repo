#!/bin/sh
# Extract Git-critical fields from project-repositories.yaml (constrained layout only).
#
# Usage:
#   extract-project-map.sh <project-map.yaml>              # list: name<TAB>clone_url<TAB>default_branch
#   extract-project-map.sh <project-map.yaml> --names      # names only, one per line
#   extract-project-map.sh <project-map.yaml> --get <name> # single record (same TAB format)
#
# Rejects unsupported YAML for critical fields. Exit 0 with no output when repositories: [].

set -e

MAP=$1
MODE=${2:-list}

fail() {
	printf '%s\n' "$1" >&2
	exit 1
}

[ -n "$MAP" ] && [ -f "$MAP" ] || fail "project map not found: $MAP"

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT INT HUP TERM
tr -d '\r' < "$MAP" > "$TMP"

# Exactly one version declaration.
version_exact=$(grep -cE '^version:[[:space:]]+1[[:space:]]*$' "$TMP" 2>/dev/null) || version_exact=0
version_total=$(grep -cE '^version:' "$TMP" 2>/dev/null) || version_total=0
[ "$version_exact" -eq 1 ] || fail "unsupported or missing version (expected exactly one 'version: 1' line)"
[ "$version_total" -eq 1 ] || fail "duplicate or conflicting version declaration"

# Reject inline comments on Git-critical field lines (before any stripping).
critical_comment() {
	pattern=$1
	label=$2
	if grep -E "$pattern" "$TMP" | grep -qE '[[:space:]]#'; then
		fail "inline comments are not supported on $label"
	fi
}
critical_comment '^  - name: ' 'name'
critical_comment '^      clone_url: ' 'clone_url'
critical_comment '^      default_branch: ' 'default_branch'

# Empty repositories: [] only supported flow form.
if grep -qE '^repositories:[[:space:]]*\[[[:space:]]*\][[:space:]]*$' "$TMP"; then
	if grep -qE '^[[:space:]]+-[[:space:]]+name:' "$TMP"; then
		fail "ambiguous project map: both repositories: [] and repository entries"
	fi
	exit 0
fi

grep -qE '^repositories:[[:space:]]*$' "$TMP" || \
	fail "unsupported repositories declaration (expected block list or repositories: [])"

repos_header_count=$(grep -cE '^repositories:[[:space:]]*$' "$TMP" 2>/dev/null) || repos_header_count=0
[ "$repos_header_count" -eq 1 ] || fail "duplicate repositories declaration"

repositories_line_count=$(grep -cE '^repositories:' "$TMP" 2>/dev/null) || repositories_line_count=0
[ "$repositories_line_count" -eq 1 ] || fail "duplicate repositories declaration"

if grep -qE '^repositories:[[:space:]]*\[' "$TMP"; then
	fail "flow-style repositories list is only supported for repositories: []"
fi

# Reject mis-indented critical-field lookalikes.
if grep -qE '^ - name:|^- name:|^   - name:|^    - name:' "$TMP"; then
	fail "incorrect indentation for name (expected exactly two spaces before '- name:')"
fi
if grep -qE '^    clone_url:|^   clone_url:|^     clone_url:' "$TMP"; then
	fail "incorrect indentation for clone_url (expected exactly six spaces)"
fi
if grep -qE '^    default_branch:|^   default_branch:|^     default_branch:' "$TMP"; then
	fail "incorrect indentation for default_branch (expected exactly six spaces)"
fi

awk -v mode="$MODE" -v get_name="${3:-}" '
BEGIN {
	err = 0
	in_repositories = 0
	in_repo = 0
	in_git = 0
	repo_count = 0
	name = ""
	clone = ""
	branch = ""
	git_seen = 0
	found = 0
}

function fail(msg) {
	if (!err) printf "%s\n", msg > "/dev/stderr"
	err = 1
	exit 1
}

function validate_name(n) {
	if (n == "") fail("repository entry missing name")
	if (n !~ /^[A-Za-z0-9][A-Za-z0-9._-]*$/) fail("invalid repository name: " n)
	if (n in seen) fail("duplicate repository name: " n)
	seen[n] = 1
}

function validate_scalar(val, label) {
	if (val == "") fail("missing " label)
	if (val ~ /^[&*]/) fail("anchors and aliases are not supported on " label)
	if (val ~ /^["'\'']/) fail("quoted scalars are not supported on " label)
	if (val ~ /^-/) fail("option-like values are not supported on " label)
	if (val ~ /#/) fail("inline comments are not supported on " label)
	if (val ~ /^[|>]|^\{/) fail("unsupported formatting for " label)
}

function flush() {
	if (!in_repo) return
	if (name == "") fail("repository entry missing name")
	if (clone == "" || branch == "") fail("repository " name " missing git.clone_url or git.default_branch")
	validate_name(name)
	validate_scalar(clone, "clone_url for " name)
	validate_scalar(branch, "default_branch for " name)
	repo_count++
	buffer[repo_count] = name "\t" clone "\t" branch
	buffer_name[repo_count] = name
	in_repo = 0
	in_git = 0
	name = ""
	clone = ""
	branch = ""
	git_seen = 0
}

/^version:/ { next }

/^repositories:[[:space:]]*$/ {
	in_repositories = 1
	next
}

/^$/ { next }

/^[^[:space:]#]/ {
	if (in_repositories) {
		flush()
		fail("unsupported top-level section after repositories: " $0)
	}
	fail("unsupported top-level key before repositories: " $0)
}

/^  - name: / {
	if (!in_repositories) fail("repository entry outside repositories block")
	flush()
	in_repo = 1
	in_git = 0
	git_seen = 0
	sub(/^  - name: /, "")
	if ($0 ~ /#/) fail("inline comments are not supported on name")
	if ($0 ~ /^[&*]/) fail("anchors and aliases are not supported on name")
	if ($0 ~ /^["'\'']/) fail("quoted scalars are not supported on name")
	name = $0
	next
}

in_repo && /^    git:[[:space:]]*$/ {
	if (git_seen) fail("duplicate git block for repository " (name == "" ? "?" : name))
	git_seen = 1
	in_git = 1
	next
}

in_repo && in_git && /^      clone_url: / {
	sub(/^      clone_url: /, "")
	if ($0 ~ /#/) fail("inline comments are not supported on clone_url for " name)
	if (clone != "") fail("duplicate clone_url for repository " name)
	clone = $0
	next
}

in_repo && in_git && /^      default_branch: / {
	sub(/^      default_branch: /, "")
	if ($0 ~ /#/) fail("inline comments are not supported on default_branch for " name)
	if (branch != "") fail("duplicate default_branch for repository " name)
	branch = $0
	next
}

in_repo && in_git && /^      / {
	fail("unsupported git field formatting in repository " (name == "" ? "?" : name))
}

in_repo && /^    / && !/^    git:/ {
	in_git = 0
}

in_repo && /^  - / && !/^  - name: / {
	fail("unsupported repository list formatting (expected \"  - name: ...\")")
}

in_repositories && /^  / && !in_repo {
	fail("unsupported content in repositories block")
}

END {
	if (err) exit 1
	flush()
	if (repo_count == 0) fail("no repository entries found in project map")
	for (i = 1; i <= repo_count; i++) {
		if (mode == "--get") {
			if (buffer_name[i] == get_name) {
				print buffer[i]
				found = 1
			}
		} else if (mode == "--names") {
			print buffer_name[i]
		} else {
			print buffer[i]
		}
	}
	if (mode == "--get" && !found && get_name != "") {
		fail("unknown repository in project map: " get_name)
	}
}
' "$TMP"
