# Convo Memory — Three-Layer Memory Compression

OptMem-style memory compression for all convo folders (Bench 3.0). Keeps the read path fast no matter how many session notes accumulate.

## What it does

Every eligible convo folder gets three memory layers:

```
convos/<topic>/
├── YYMMDD-*.md          Layer 0 (log)   — session notes, written by /note as always, never touched
├── _memory-index.md     Layer 1 (index) — detailed evidence with [YYMMDD] source citations, append-heavy
└── _memory-master.md    Layer 2 (wake)  — compact summary, ~60 line cap, regenerated from the index
```

Nightly, the script finds notes newer than each folder's watermark (tracked in `state.json`), appends their content to the folder's `_memory-index.md` (Phase 1), then regenerates the compact `_memory-master.md` from the index (Phase 2). Both phases run on Claude Haiku.

The `>>` topic convention reads `_memory-master.md` + only the notes newer than its watermark — instead of every note in the folder. See `master-instructions.md` → "The >> topic convention".

## Eligibility

- Top-level folders in `convos/` with ≥5 notes matching `YYMMDD-*.md` (override with `--min-notes`)
- Excluded: `Templates`, `~archive`, `~empty`, `daily-log` (machine-generated, has its own rollups)
- Subfolders are ignored — only top-level convo folders are processed

## Safety rules

- The script writes ONLY `_memory-index.md`, `_memory-master.md`, and `state.json`. Raw notes are read-only.
- Never hand-edit `_memory-*.md` files — they are machine-maintained and regenerated.
- Guards: index update is rejected if the `- [YYMMDD]` bullet count would decrease; master is rejected above 90 lines or with a missing header. On rejection nothing is written and the watermark stays put (retried next run).
- Any bad write is one `git checkout` away from recovery (memory files are git-tracked).

## Schedule

Nightly at 02:30 via launchd (`com.bench.convo-memory.plist`).

Install (replace `__BENCH_PATH__` in the plist with your bench's absolute path first):
```bash
sed "s|__BENCH_PATH__|$(pwd)|g" actions/recurring/convo-memory/com.bench.convo-memory.plist > ~/Library/LaunchAgents/com.bench.convo-memory.plist
launchctl load ~/Library/LaunchAgents/com.bench.convo-memory.plist
```

## Manual usage

```bash
python3 actions/recurring/convo-memory/convo_memory.py --all                  # incremental, all folders
python3 actions/recurring/convo-memory/convo_memory.py --folder music        # single folder
python3 actions/recurring/convo-memory/convo_memory.py --folder music --bootstrap   # full rebuild
python3 actions/recurring/convo-memory/convo_memory.py --all --dry-run       # preview
python3 actions/recurring/convo-memory/convo_memory.py --all --commit        # + narrow git commit/push
```

Bootstrap is resumable — the watermark advances after each batch of 10 notes, so an interrupted run continues where it stopped.

## Keys

Only `ANTHROPIC_API_KEY` from `config/keys.env`.

## Logs & state

- `trigger.log` in this folder (persistent), `/tmp/convo-memory.log|.err` (launchd)
- `state.json` — per-folder watermarks: `{"folders": {"<topic>": {"last_note": ..., "last_run": ..., "notes_indexed": N}}}`

## Git behavior

No auto-commit by default — memory file updates ride along with the normal `/push` flow. Enable nightly auto-commit by adding `--commit` to the plist's ProgramArguments.

## Related

- OptMem: https://github.com/VictorTaelin/OptMem
