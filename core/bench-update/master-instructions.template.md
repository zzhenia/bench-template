# Master instructions

The first file every session reads on this bench. `CLAUDE.md` holds the rules
that load automatically; this file says what the bench is, where things live and
where to look.

## What this bench is for

<One or two lines: whose work, which clients or subjects.>

## Where things live

| Folder | Holds |
|---|---|
| `convos/<topic>/` | dated session notes, one folder per conversation |
| `tools/recurring/<name>/`, `tools/on-demand/<name>/` | this bench's tools, one folder each, `instructions.md` first |
| `core/` | what every bench shares: skills, tools, rules, `/update`. Changed only in the bench that publishes it |
| `personal/skills/<name>/` | this bench's own skills; `personal/overlays/<skill>.md` changes a core skill here |
| `skills/` | links only, made by `core/bin/link-skills.sh`; never edit or add a folder here |
| `config/` | this bench's settings and keys |

## Where to look, in order

1. A tool for the request: `tools/` (read its `instructions.md` before answering).
2. A skill for it: `skills/`.
3. Past work: `convos/<topic>/_memory-master.md`, then `_memory-index.md`, then the notes.
4. This bench's other sources: `personal/overlays/lookup.md`.
