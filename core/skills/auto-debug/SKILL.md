---
name: auto-debug
description: Turn on, turn off or check auto-debug for a tool — a watcher that starts Claude Code to fix whatever is listed in that tool's BUGS.md. Use when asked to watch a BUGS.md, auto-fix a tool's bug list, or see which tools are being watched.
---

If `personal/overlays/auto-debug.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Read `core/tools/auto-debug/instructions.md`, then run `python3 core/tools/auto-debug/auto_debug.py {start|stop|status} [tool-slug]` and report the result in one line.
