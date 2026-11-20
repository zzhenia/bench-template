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

Nightly, the script finds notes newer than each folder's watermark (tracked in `state/convo-memory/state.json`), appends their content to the folder's `_memory-index.md` (Phase 1), then regenerates the compact `_memory-master.md` from the index (Phase 2). Both phases run as AI operation `memory`: through the bench's AI profile (`lib/bench_ai.py` + `config/ai-profile.json`) when the bench has one, otherwise through the `claude` CLI on the bench's own login (`.claude-login`) with the model alias in `CONVO_MEMORY_MODEL` (`config/bench.env`, default `haiku`). Each bench runs its own job over its own `convos/`.

The `>>` topic convention reads `_memory-master.md` + only the notes newer than its watermark — instead of every note in the folder.

## Eligibility

- Top-level folders in `convos/` with ≥5 notes matching `YYMMDD-*.md` (override with `--min-notes`)
- Excluded: `Templates`, `~archive`, `~empty`, `daily-log` (machine-generated, has its own rollups)
- Subfolders are ignored

## Safety rules

- The script writes ONLY `_memory-index.md`, `_memory-master.md`, and `state/convo-memory/`. Raw notes are read-only.
- Never hand-edit `_memory-*.md` files — they are machine-maintained and regenerated.
- Guards: index update is rejected if the `- [YYMMDD]` bullet count would decrease; master is rejected above 90 lines or with a missing header. On rejection nothing is written and the watermark stays put (retried next run).
- Any bad write is one `git checkout` away from recovery (memory files are git-tracked).

## Schedule

Nightly at 02:30 via launchd (`com.bench.<slug>.convo-memory`, from `schedule.plist`), on Homebrew Python (3.10+; python-repin keeps the version pinned). Installed by `core/bin/install-schedules.sh`.

## Manual usage

```bash
python3 core/tools/convo-memory/convo_memory.py --all                  # incremental, all folders
python3 core/tools/convo-memory/convo_memory.py --folder music        # single folder
python3 core/tools/convo-memory/convo_memory.py --folder music --bootstrap   # full rebuild
python3 core/tools/convo-memory/convo_memory.py --all --dry-run       # preview
python3 core/tools/convo-memory/convo_memory.py --all --commit        # + narrow git commit/push
```

Bootstrap is resumable — the watermark advances after each batch of 10 notes, so an interrupted run continues where it stopped.

## Settings

- `CONVO_MEMORY_MODEL` in `config/bench.env` — model alias for the `claude` CLI path only (default `haiku`). With an AI profile, switch the `memory` operation there instead.
- No API key: the CLI path strips `ANTHROPIC_API_KEY` so runs bill the subscription.

## Logs & state

- `state/convo-memory/trigger.log` (persistent), `/tmp/com.bench.<slug>.convo-memory.log|.err` (launchd)
- `state/convo-memory/state.json` — per-folder watermarks: `{"folders": {"<topic>": {"last_note": ..., "last_run": ..., "notes_indexed": N}}}`

## Git behavior

No auto-commit by default — memory file updates ride along with the normal `/push` flow. Enable nightly auto-commit by adding `--commit` to `schedule.plist`'s ProgramArguments.

## Related

- OptMem: https://github.com/VictorTaelin/OptMem
