---
name: nb
description: Remove hard line breaks from text — unwrap text that was wrapped at a fixed column (pasted from a PDF, email, terminal, subtitle file, or code comment) so each paragraph becomes one continuous line. Preserves blank lines, bullets, numbered lists, headings, quotes, and indented code. Use when asked to remove line breaks, unwrap, unhardwrap, reflow, join lines, fix wrapped text, or clean up pasted text. Triggers on /nb.
model: haiku
---

Run `scripts/nobreaks.sh` once. Do nothing else.

This command exists so Zhenia can copy text out of a terminal. It is not an
invitation to investigate anything.

For the clipboard, `!nb` is faster than `/nb` — it runs the same script directly,
with no model turn. `/nb` is for text or a path handed over in the message.

| They gave you | Run |
|---|---|
| Nothing (`/nb` bare) | `scripts/nobreaks.sh -p` |
| Text after `/nb` | write it to the scratchpad, then `scripts/nobreaks.sh <file>` |
| A file path | `scripts/nobreaks.sh <path>` |

## Hard rules

- **One Bash call.** Not two. No `-d` dump, no test files, no `cat`, no `ls`.
- **Never edit the script**, even when it leaves something unjoined. If the output
  looks wrong, say so in one sentence and stop. Zhenia will ask if they want it fixed.
- **Never reimplement the joining** in sed, awk, or by hand.
- **Say almost nothing.** Clipboard mode: repeat the script's one-line confirmation
  and stop. File/inline mode: the unwrapped text in a fenced block and stop. No
  explanation of what changed, no notes on what it preserved, no follow-up offers.
- If the script reports `nothing to join` or an empty clipboard, repeat that line
  verbatim and stop. Do not diagnose it.

Use `-p` (not bare `nobreaks`) for the clipboard — stdin is not a TTY in a tool call,
so the bare form hangs until timeout.
