#!/usr/bin/env bash
# jira — minimal, reliable Jira REST v3 helper for agents.
#
# An agent's generic `fetch` tool can do a GET but stumbles on an
# authenticated POST with a v3 Atlassian Document Format (ADF) body — which is
# why creating issues failed. This wrapper handles auth + ADF so an agent only
# has to run one command. Credentials come from the environment
# (`source config/keys.env` first).
#
# Usage:
#   scripts/jira.sh get <KEY>
#   scripts/jira.sh create-child <PARENT_KEY> "<summary>" ["<description>"]
#   scripts/jira.sh create <PROJECT_KEY> "<IssueType>" "<summary>" ["<description>"]
#
# HIERARCHY RULE (enforced, never bypass):
#   Epic -> Task -> Sub-task. A child never skips a level.
#   Parent is an Epic      -> child is a **Task**   (never a Sub-task)
#   Parent is a Task/Story -> child is a Sub-task
#   Parent is a Sub-task   -> refused (nothing nests under a Sub-task)
#   `create-child` looks the parent up and picks the type for you. Do not pass
#   an explicit type. `create-subtask` is a deprecated alias for `create-child`.
#
# Examples:
#   scripts/jira.sh get PROJ-123
#   scripts/jira.sh create-child PROJ-123 "Add export button" \
#     "Let users export the report as CSV."
#   # PROJ-123 is an Epic, so that creates a **Task**, not a Sub-task.
#
# Options (env):
#   DRY_RUN=1   build and print the payload + target, but send nothing.
#
# Credentials (read from env):
#   JIRA_URL          e.g. https://your-workspace.atlassian.net
#   JIRA_EMAIL
#   JIRA_API_TOKEN
set -euo pipefail

JURL="${JIRA_URL:-}"
JEMAIL="${JIRA_EMAIL:-}"
JTOKEN="${JIRA_API_TOKEN:-}"
JURL="${JURL%/}"

if [ -z "$JURL" ] || [ -z "$JEMAIL" ] || [ -z "$JTOKEN" ]; then
  echo "error: missing Jira credentials in environment." >&2
  echo "  need JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN" >&2
  exit 2
fi

usage() { sed -n '2,35p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

cmd="${1:-}"; shift || true

# HTTP via curl (uses the system CA store — Homebrew python lacks one). JSON
# payloads are built separately by python3 (no network). Args pass via env to
# avoid shell-quoting pitfalls. Usage: do_req METHOD PATH [JSON_BODY]
do_req() {
  local method="$1" path="$2" body="${3:-}"
  local url="${JURL}${path}"
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "[dry-run] ${method} ${url}"
    if [ -n "$body" ]; then
      echo "[dry-run] body:"; printf '%s' "$body" | python3 -m json.tool
    fi
    return 0
  fi
  local args=(-sS -w $'\n%{http_code}' -u "${JEMAIL}:${JTOKEN}" -X "$method" \
              -H "Accept: application/json")
  [ -n "$body" ] && args+=(-H "Content-Type: application/json" --data "$body")
  local resp code out
  resp="$(curl "${args[@]}" "$url")"
  code="${resp##*$'\n'}"; out="${resp%$'\n'*}"
  if [ "$code" -ge 400 ]; then
    echo "HTTP $code" >&2
    printf '%s\n' "$out" | python3 -m json.tool 2>/dev/null >&2 || printf '%s\n' "$out" >&2
    return 1
  fi
  printf '%s\n' "$out" | python3 -m json.tool 2>/dev/null || printf '%s\n' "$out"
}

# Build a v3 create payload (ADF description) via python3 and hand back JSON.
build_payload() {
  J_PROJECT="$1" J_TYPE="$2" J_SUMMARY="$3" J_DESC="${4:-}" J_PARENT="${5:-}" python3 - <<'PY'
import os, json
fields = {
    "project": {"key": os.environ["J_PROJECT"]},
    "issuetype": {"name": os.environ["J_TYPE"]},
    "summary": os.environ["J_SUMMARY"],
}
if os.environ.get("J_PARENT"):
    fields["parent"] = {"key": os.environ["J_PARENT"]}
desc = os.environ.get("J_DESC") or ""
if desc:
    fields["description"] = {
        "type": "doc", "version": 1,
        "content": [{"type": "paragraph",
                     "content": [{"type": "text", "text": desc}]}],
    }
print(json.dumps({"fields": fields}))
PY
}

# Resolve the correct child issue type for a parent, enforcing Epic -> Task ->
# Sub-task. Prints the type name on stdout; exits 1 with a message on stderr if
# the parent cannot legally have a child. This read always runs, even under
# DRY_RUN — only writes are gated.
resolve_child_type() {
  local parent="$1" pjson
  pjson="$(DRY_RUN=0 do_req GET "/rest/api/3/issue/${parent}?fields=issuetype")" || {
    echo "error: could not read parent ${parent}" >&2; return 1; }
  printf '%s' "$pjson" | python3 -c '
import sys, json
it = json.load(sys.stdin)["fields"]["issuetype"]
name = it.get("name", "?")
if it.get("subtask"):
    sys.stderr.write(
        "error: parent is a Sub-task (%s). Nothing nests under a Sub-task -- "
        "hierarchy is Epic -> Task -> Sub-task.\n" % name)
    sys.exit(1)
# hierarchyLevel: 1 = Epic, 0 = Task/Story, -1 = Sub-task
print("Task" if it.get("hierarchyLevel", 0) >= 1 else "Sub-task")
' || return 1
}

# Create an issue and, on success, print "Created <KEY> — <browse url>".
do_create() {
  local payload="$1" out key
  out="$(do_req POST "/rest/api/3/issue" "$payload")" || { printf '%s\n' "$out"; return 1; }
  if [ "${DRY_RUN:-0}" = "1" ]; then printf '%s\n' "$out"; return 0; fi
  key="$(printf '%s' "$out" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("key",""))' 2>/dev/null)"
  if [ -n "$key" ]; then echo "Created ${key} — ${JURL}/browse/${key}"; else printf '%s\n' "$out"; fi
}

case "$cmd" in
  get)
    key="${1:?usage: jira.sh get <KEY>}"
    do_req GET "/rest/api/3/issue/${key}?fields=summary,issuetype,parent,status"
    ;;
  transitions)
    # list available transitions (names) for an issue — read-only
    key="${1:?usage: jira.sh transitions <KEY>}"
    do_req GET "/rest/api/3/issue/${key}/transitions" \
      | python3 -c 'import sys,json; [print(t["id"],"->",t["name"]) for t in json.load(sys.stdin).get("transitions",[])]' 2>/dev/null \
      || echo "(could not parse transitions)"
    ;;
  transition)
    # move an issue to a target status by NAME (resolves the transition id)
    key="${1:?usage: jira.sh transition <KEY> \"<Status Name>\"}"
    target="${2:?target status name required}"
    # the lookup is a read — always run it, even under DRY_RUN (only the POST is gated)
    tjson="$(DRY_RUN=0 do_req GET "/rest/api/3/issue/${key}/transitions")" || { printf '%s\n' "$tjson"; exit 1; }
    tid="$(printf '%s' "$tjson" | J_TARGET="$target" python3 -c '
import sys,os,json
target=os.environ["J_TARGET"].strip().lower()
for t in json.load(sys.stdin).get("transitions",[]):
    if t["name"].strip().lower()==target or t.get("to",{}).get("name","").strip().lower()==target:
        print(t["id"]); break
')"
    if [ -z "$tid" ]; then
      echo "error: no transition to \"$target\" available for $key. Available:" >&2
      printf '%s' "$tjson" | python3 -c 'import sys,json; [print(" -",t["name"]) for t in json.load(sys.stdin).get("transitions",[])]' >&2 2>/dev/null
      exit 1
    fi
    if [ "${DRY_RUN:-0}" = "1" ]; then echo "[dry-run] would POST transition id=$tid (\"$target\") to $key"; exit 0; fi
    do_req POST "/rest/api/3/issue/${key}/transitions" "{\"transition\":{\"id\":\"${tid}\"}}" \
      && echo "Moved ${key} -> ${target}"
    ;;
  rename)
    # change an issue's summary (title)
    key="${1:?usage: jira.sh rename <KEY> \"<new summary>\"}"
    newsum="${2:?new summary required}"
    payload="$(J_S="$newsum" python3 -c 'import os,json; print(json.dumps({"fields":{"summary":os.environ["J_S"]}}))')"
    if [ "${DRY_RUN:-0}" = "1" ]; then echo "[dry-run] would PUT summary of $key -> \"$newsum\""; exit 0; fi
    do_req PUT "/rest/api/3/issue/${key}" "$payload" && echo "Renamed ${key} -> \"${newsum}\""
    ;;
  delete)
    key="${1:?usage: jira.sh delete <KEY>}"
    if [ "${DRY_RUN:-0}" = "1" ]; then echo "[dry-run] would DELETE $key"; exit 0; fi
    do_req DELETE "/rest/api/3/issue/${key}" && echo "Deleted ${key}"
    ;;
  create-child|create-subtask)
    # Epic -> Task -> Sub-task. The child type is derived from the parent, never
    # passed in, so a child under an Epic can never come out as a Sub-task.
    parent="${1:?usage: jira.sh create-child <PARENT_KEY> \"<summary>\" [\"<desc>\"]}"
    summary="${2:?summary required}"; desc="${3:-}"
    project="${parent%%-*}"
    ctype="$(resolve_child_type "$parent")" || exit 1
    echo "parent ${parent} -> creating a ${ctype}" >&2
    do_create "$(build_payload "$project" "$ctype" "$summary" "$desc" "$parent")"
    ;;
  create)
    project="${1:?usage: jira.sh create <PROJECT_KEY> \"<IssueType>\" \"<summary>\" [\"<desc>\"]}"
    itype="${2:?issue type required}"; summary="${3:?summary required}"; desc="${4:-}"
    case "$(printf '%s' "$itype" | tr '[:upper:]' '[:lower:]' | tr -d ' -_')" in
      subtask)
        echo "error: 'create' makes parentless issues and a Sub-task must have a parent." >&2
        echo "  use: jira.sh create-child <PARENT_KEY> \"<summary>\" [\"<desc>\"]" >&2
        echo "  (it derives the type: Epic -> Task, Task/Story -> Sub-task)" >&2
        exit 1 ;;
    esac
    do_create "$(build_payload "$project" "$itype" "$summary" "$desc" "")"
    ;;
  ""|-h|--help|help) usage ;;
  *) echo "unknown command: $cmd" >&2; usage ;;
esac
