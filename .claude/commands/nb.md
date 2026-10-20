---
name: nb
description: Remove hard line breaks from text — unwrap text that was wrapped at a fixed column (pasted from a PDF, email, terminal, subtitle file, or code comment) so each paragraph becomes one continuous line. Preserves blank lines, bullets, numbered lists, headings, quotes, and indented code. Use when asked to remove line breaks, unwrap, unhardwrap, reflow, join lines, fix wrapped text, or clean up pasted text. Triggers on /nb.
model: haiku
---

Unwrap hard-wrapped text using `scripts/nobreaks.sh` (referred to below as `nobreaks`; it is
also on PATH under that name when symlinked into `~/.local/bin`).

**Never reimplement this in sed, awk, or by hand-editing the text yourself.** The script is
the single source of truth for the join rules. If it gets something wrong, fix the script.

## Pick the mode from what the user gave you

| They gave you | Run |
|---|---|
| Nothing (`/nb` bare) | `nobreaks -p` — reads clipboard, writes clipboard |
| Text inline after `/nb`, or pasted in chat | Write it to a scratchpad file, then `nobreaks <file>`, and show the result in a fenced block |
| A file path | `nobreaks <path>` — prints to stdout, leaves the file alone |
| A file path + "in place" / "fix the file" | `cp -p <path> <path>.bak && nobreaks <path> > <path>.tmp && cat <path>.tmp > <path> && rm <path>.tmp` — confirm first if the file is tracked in git |

**In-place editing is for prose files only — never source code.** Every unindented line is a
join candidate, so a `.py`/`.sh`/`.js` file comes back as `import os import sys`. Use `cat >`
rather than `mv`: `mv` replaces the file and drops its mode (755 → 644, so a script stops
being executable), while `cat >` keeps the inode, mode, and any symlink. The `.bak` is the undo.

`$ARGUMENTS` is whatever followed `/nb`. Treat it as a file path only if it resolves
to an existing file; otherwise it is the text to unwrap.

Always write inline text to a file rather than piping it through a shell string — text with
quotes, backticks, `$`, or emoji gets mangled by shell interpolation. Use the session
scratchpad directory.

## What it does and does not join

Joins consecutive lines into one paragraph, separated by a single space. Left alone:

- blank lines (paragraph breaks)
- bullets — `-`, `*`, `+`, `•`
- numbered items — `1.`, `1)` (up to 3 digits; a mid-paragraph `1945.` is prose, not a list)
- headings (`# ` … `###### `) and quotes (`>`) — `#42` is not a heading
- setext underlines and rules — `===`, `---`, `***`, `___`
- fenced code blocks — triple-backtick or `~~~` fences, fences and contents alike
- lines indented 4+ spaces or a tab (real code blocks)

Lines indented 1–3 spaces are treated as wrap artifacts and get joined — PDFs and emails
routinely pad wrapped lines. That includes a wrapped list item's continuation, which is folded
back into its bullet; the indent is kept when it marks a *nested* list item, so list nesting
survives. CRLF is normalized, trailing whitespace (including a non-breaking space) stripped, a
word split across lines by a hyphen rejoined (`hyphen-` + `ated` → `hyphenated`), runs of blank
lines collapsed to one.

## Flags

```
nobreaks              # clipboard → clipboard (only when stdin is a TTY or closed)
nobreaks FILE...      # file(s) → stdout
nobreaks -p           # force clipboard input  (use this from Claude Code — stdin is not a TTY here)
nobreaks -c           # force clipboard output
nobreaks -d           # dump input with line endings shown, no processing
nobreaks -h           # help
```

**Use `-p`, not bare `nobreaks`, when running from a tool call.** Stdin is not a TTY in a
Claude Code Bash call, so bare `nobreaks` falls through to reading stdin and hangs until the
120s timeout.

## When nothing gets joined

The script reports `N lines in, N out — nothing to join` whenever no line was actually joined.
The two counts are total lines, so they can differ from each other even in that message — blank
lines may have been collapsed. Do not guess at the cause — run
`nobreaks -d` (or `-p -d` for the clipboard) to see the raw input with `$` at each line end
and `^M` for CR. Then check, in order:

1. Every line starts with a bullet, number, `#`, or `>` — correct behavior, nothing to join.
2. Lines are indented 4+ spaces or a tab — being treated as a code block. If it is really
   prose from a PDF, widen the soft-indent rule in the script (the `s/^[ ]{1,3}...//mg` pass).
3. There are no `\n` at all — the text is one line already, or uses U+2028/U+2029 line
   separators, which the script does not currently handle. Add them to the normalize step.
4. The script exited 1 with `clipboard is empty or holds no text` — the clipboard is empty or
   holds an image / rich-text-only flavor with no plain-text representation. Nothing was
   overwritten; ask the user to copy the text again as plain text.

## Reporting back

Show the unwrapped text, not a description of it. For the clipboard modes, the script's own
one-line confirmation (`✓ 9 lines → 3 → clipboard`) is the whole report — do not add to it.
