---
name: yt-transcript
description: Fetch a YouTube video's transcript (captions) as plain text, optionally with timestamps. Use whenever a task needs what is said in a YouTube video — summarising, quoting, research, script references. Use this before any ad-hoc yt-dlp call.
---

If `personal/overlays/yt-transcript.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Read `core/tools/yt-transcript/instructions.md`, then run:

```
python3 core/tools/yt-transcript/run.py <url-or-id> [--timestamps] [--output FILE]
```

The first run builds its venv under `state/yt-transcript/` (about a minute). Report the saved path.
