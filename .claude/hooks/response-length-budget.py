#!/usr/bin/env python3
"""Stop hook: enforce a response length budget on Claude's replies.

Reads the hook payload on stdin, finds the assistant message that is about to be
shown, and measures its prose. Over budget -> emit decision:"block" so the turn
continues and the reply gets rewritten short before you ever read it.

Why a hook and not a CLAUDE.md rule: "keep answers short" written as an
instruction is advisory, and models drift back to verbose under load no matter
how many times it is restated. A hook is enforcement — the harness runs it, so
the long reply is rejected and rewritten before it reaches your terminal.

Fenced code blocks are exempt: pasted commands and diffs are not the problem,
prose is. Everything else counts, tables included.

Tuning
------
RESPONSE_BUDGET_CHARS   prose budget in characters (default 600)
RESPONSE_BUDGET_OFF=1   disable for a session without editing settings.json

600 is deliberately tight — roughly a short paragraph plus a line or two. Raise
it if your work needs more narration per turn. To calibrate against your own
taste rather than guessing, measure the replies you found too long and the ones
you were happy with, and set the budget in the gap between them.

Portable by design: no absolute paths, no machine-specific assumptions.
"""
import json
import os
import re
import sys

DEFAULT_BUDGET = 600
PROJECT_COPY = os.path.join(".claude", "hooks", "response-length-budget.py")


def superseded_by_project_copy() -> bool:
    """True if this is a personal copy and the project ships its own.

    Both ~/.claude/settings.json and a project's .claude/settings.json can
    register this hook. Without this check both fire and the same reply is
    rejected twice with duplicate reasons. The project copy wins, since a repo
    may tune the budget for its own house style.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_dir:
        return False
    project_hook = os.path.join(project_dir, PROJECT_COPY)
    if not os.path.isfile(project_hook):
        return False
    try:
        return os.path.realpath(project_hook) != os.path.realpath(__file__)
    except OSError:
        return False


def visible_prose(text: str) -> str:
    """Strip fenced code blocks; return what's left."""
    return re.sub(r"```.*?(?:```|\Z)", "", text, flags=re.DOTALL)


def last_assistant_text(transcript_path: str) -> str:
    """Text blocks of the final assistant message in the transcript."""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return ""

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        if isinstance(content, str):
            return content
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        # A tool-call-only message has no text; keep walking back.
        if any(p.strip() for p in parts):
            return "\n".join(parts)
    return ""


def main() -> int:
    if os.environ.get("RESPONSE_BUDGET_OFF") or superseded_by_project_copy():
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    # Already rewritten once this turn — let it through, never loop.
    if payload.get("stop_hook_active"):
        return 0

    text = last_assistant_text(payload.get("transcript_path", ""))
    if not text:
        return 0

    try:
        budget = int(os.environ.get("RESPONSE_BUDGET_CHARS", DEFAULT_BUDGET))
    except ValueError:
        budget = DEFAULT_BUDGET

    prose = visible_prose(text)
    used = len(prose.strip())
    if used <= budget:
        return 0

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"Your reply is {used} characters of prose against a {budget} budget "
            f"(fenced code excluded). It is too long and the user has not seen "
            f"it yet.\n\n"
            f"Rewrite it now: lead with the outcome, keep the numbers and "
            f"anything needing their decision, and cut the rest. Drop recaps of "
            f"what they already know, caveats about caveats, section headers, "
            f"and restatements of the question. Detail belongs in the session "
            f"note, not the terminal. Do not mention this hook or narrate the "
            f"rewrite — just reply short."
        ),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
