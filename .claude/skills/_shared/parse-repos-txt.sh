#!/bin/sh
# Parse repos.txt: one repository name per line.
#
# Usage:
#   parse-repos-txt.sh <repos.txt> [--validate-map <project-map.yaml>]
#
# Prints one name per line. Validates duplicates and (optionally) membership in project map.

set -e

FILE=$1
MODE=$2
MAP=$3

[ -n "$FILE" ] && [ -f "$FILE" ] || {
	printf 'repos.txt not found: %s\n' "$FILE" >&2
	exit 1
}

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
EXTRACT="$SCRIPT_DIR/extract-project-map.sh"

TMP_SEEN=$(mktemp)
trap 'rm -f "$TMP_SEEN"' EXIT INT HUP TERM

while IFS= read -r line || [ -n "$line" ]; do
	line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
	[ -z "$line" ] && continue
	case $line in
	\#*) continue ;;
	esac
	printf '%s' "$line" | grep -qE '^[A-Za-z0-9][A-Za-z0-9._-]*$' || {
		printf 'invalid repository name in repos.txt: %s\n' "$line" >&2
		exit 1
	}
	if grep -qxF "$line" "$TMP_SEEN" 2>/dev/null; then
		printf 'duplicate repository name in repos.txt: %s\n' "$line" >&2
		exit 1
	fi
	printf '%s\n' "$line" >> "$TMP_SEEN"
	printf '%s\n' "$line"
	done < "$FILE"

if [ ! -s "$TMP_SEEN" ]; then
	printf 'repos.txt has no repository entries\n' >&2
	exit 1
fi

if [ "$MODE" = "--validate-map" ]; then
	[ -n "$MAP" ] && [ -f "$MAP" ] || {
		printf 'project map not found: %s\n' "$MAP" >&2
		exit 1
	}
	[ -x "$EXTRACT" ] || {
		printf 'missing extract helper: %s\n' "$EXTRACT" >&2
		exit 1
	}
	MAP_NAMES=$(mktemp)
	trap 'rm -f "$TMP_SEEN" "$MAP_NAMES"' EXIT INT HUP TERM
	"$EXTRACT" "$MAP" --names | sort -u > "$MAP_NAMES"
	while IFS= read -r name || [ -n "$name" ]; do
		grep -qxF "$name" "$MAP_NAMES" || {
			printf 'unknown repository in repos.txt: %s\n' "$name" >&2
			exit 1
		}
	done < "$TMP_SEEN"
fi
