#!/usr/bin/env bash
#
# check_doc_paths.sh — lightweight doc-path drift detector.
#
# Scans a small set of root-level docs for repo-relative path-like
# tokens (markdown links and inline code paths) and reports any that
# do not exist. Pure bash + standard POSIX tools. No dependencies.
#
# Exit code:
#   0  — all references resolve
#   1  — one or more references do not resolve
#   2  — invocation / environment error
#
# Usage:
#   scripts/ci/check_doc_paths.sh
#
# Scope intentionally small — these are the docs an agent reads first.
# Expand cautiously; widening this list will surface much more drift.

set -u

# Resolve repo root via git so the script works from any cwd.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${REPO_ROOT}" ]; then
  echo "check_doc_paths: not inside a git work tree" >&2
  exit 2
fi
cd "${REPO_ROOT}" || exit 2

DOCS=(
  "README.md"
  "CLAUDE.md"
  "AGENTS.md"
  "docs/README.md"
  "docs/skills-index.md"
)

# Documented runtime-only paths.
#
# Some paths the docs refer to are created by the platform at runtime
# and are gitignored (see .gitignore — state/* subtrees are excluded
# except for .gitkeep markers). They are documentation of a runtime
# convention, not source paths. Listing them here lets the checker
# treat them as resolvable without weakening the check for normal
# source/doc paths. Keep this list narrow.
RUNTIME_ALLOWED=(
  "state/checkpoints/platform/"
)

# Optional argument: --quiet suppresses the per-file scan header.
QUIET="0"
if [ "${1:-}" = "--quiet" ]; then
  QUIET="1"
fi

missing_count=0
checked_count=0
declare -a MISSING_REPORT=()

# extract_paths <file>
#   Emit one repo-relative path-like token per line from <file>.
#   - Pulls hrefs from markdown links (e.g. [label](path/to/file.md))
#   - Pulls inline-code tokens that look like repo-relative paths
#     (e.g. `packages/policies/approvals.py`)
#   - Ignores URLs, anchors, and placeholders containing < or >
extract_paths() {
  local file="$1"
  if [ ! -f "${file}" ]; then
    return 0
  fi

  # 1) Markdown link hrefs: [label](href)
  grep -oE '\]\([^)]+\)' "${file}" \
    | sed -E 's/^\]\(//; s/\)$//' \
    | while IFS= read -r raw; do
        # Strip trailing anchor and any title quoted after a space.
        raw="${raw%%#*}"
        raw="${raw%% *}"
        # Skip empty and external links.
        if [ -z "${raw}" ]; then continue; fi
        case "${raw}" in
          http://*|https://*|mailto:*) continue ;;
          \<*|*\>*) continue ;;
        esac
        echo "${raw}"
      done

  # 2) Inline-code tokens that look like a repo path.
  #    Matches: backtick-wrapped tokens containing a "/" and ending in
  #    one of a small set of extensions, OR ending in a "/" (a dir).
  grep -oE '`[^`]+`' "${file}" \
    | sed -E 's/^`//; s/`$//' \
    | while IFS= read -r raw; do
        if [ -z "${raw}" ]; then continue; fi
        case "${raw}" in
          \<*|*\>*) continue ;;
          http://*|https://*) continue ;;
        esac
        # Require a "/" so we don't match bare identifiers.
        case "${raw}" in
          */*) ;;
          *)   continue ;;
        esac
        # Accept tokens ending with a slash (dir) or with a known ext.
        case "${raw}" in
          */)               echo "${raw}" ;;
          *.md|*.py|*.json|*.yml|*.yaml|*.sh|*.toml|*.txt|*.swift|*.lock) echo "${raw}" ;;
          *)                : ;;
        esac
      done
}

# normalize <token>
#   - strip leading "./"
#   - strip any trailing punctuation like "." or ","
normalize() {
  local raw="$1"
  raw="${raw#./}"
  raw="${raw%[.,;:]}"
  printf '%s' "${raw}"
}

# resolve_token <doc> <token>
#   Try to resolve a path-like token to an existing file or directory.
#   Tokens that start with "/" are repo-root-relative. All other tokens
#   are tried first relative to the doc's directory, then relative to
#   the repo root, then with a leading "/" stripped. Prints the
#   resolved path on success, prints nothing on failure.
resolve_token() {
  local doc="$1"
  local raw="$2"
  local doc_dir
  doc_dir="$(dirname "${doc}")"

  local candidates=()
  case "${raw}" in
    /*)
      candidates+=( ".${raw}" "${raw#/}" )
      ;;
    *)
      if [ "${doc_dir}" = "." ] || [ -z "${doc_dir}" ]; then
        candidates+=( "${raw}" )
      else
        candidates+=( "${doc_dir}/${raw}" "${raw}" )
      fi
      ;;
  esac

  for cand in "${candidates[@]}"; do
    # Collapse ".." segments via realpath if available; otherwise use as-is.
    local resolved="${cand}"
    if command -v realpath >/dev/null 2>&1; then
      resolved="$(realpath -m --relative-to="${REPO_ROOT}" "${REPO_ROOT}/${cand}" 2>/dev/null || echo "${cand}")"
    fi
    if [ -e "${resolved}" ] || [ -d "${resolved}" ]; then
      echo "${resolved}"
      return 0
    fi
    if [ -e "${cand}" ] || [ -d "${cand}" ]; then
      echo "${cand}"
      return 0
    fi
  done
  return 1
}

for doc in "${DOCS[@]}"; do
  if [ ! -f "${doc}" ]; then
    MISSING_REPORT+=("${doc} (the doc itself is missing)")
    missing_count=$((missing_count + 1))
    continue
  fi
  if [ "${QUIET}" = "0" ]; then
    echo "scanning: ${doc}"
  fi

  # Collect and dedupe path-like tokens for this doc.
  tokens="$(extract_paths "${doc}" | sort -u)"

  while IFS= read -r token; do
    if [ -z "${token}" ]; then continue; fi
    norm="$(normalize "${token}")"
    if [ -z "${norm}" ]; then continue; fi

    checked_count=$((checked_count + 1))

    if resolve_token "${doc}" "${norm}" >/dev/null; then
      continue
    fi

    # Allow narrowly-documented runtime-only paths (see RUNTIME_ALLOWED).
    is_runtime_allowed="0"
    for allowed in "${RUNTIME_ALLOWED[@]}"; do
      if [ "${norm}" = "${allowed}" ]; then
        is_runtime_allowed="1"
        break
      fi
    done
    if [ "${is_runtime_allowed}" = "1" ]; then
      continue
    fi

    MISSING_REPORT+=("${doc} -> ${token}")
    missing_count=$((missing_count + 1))
  done <<EOF
${tokens}
EOF

done

echo
echo "check_doc_paths: scanned ${#DOCS[@]} docs, checked ${checked_count} path-like tokens."

if [ "${missing_count}" -eq 0 ]; then
  echo "check_doc_paths: OK — all references resolve."
  exit 0
fi

echo "check_doc_paths: ${missing_count} broken reference(s) found:"
for entry in "${MISSING_REPORT[@]}"; do
  echo "  - ${entry}"
done
exit 1
