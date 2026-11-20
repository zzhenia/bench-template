# Convo Memory — Eval Cases

Pass/fail checks for the memory compression pipeline.

## 1. Bootstrap fidelity
- Run `--folder <mid-size> --bootstrap` on a folder with 8-15 notes.
- PASS: `_memory-index.md` created with all 5 sections; every bullet carries a `[YYMMDD]` citation matching a real note; `_memory-master.md` under 60 lines with correct `Covers N notes through YYMMDD` watermark.
- PASS: a decision recorded in the OLDEST note is findable in the index.

## 2. Incremental update
- Add one new dated note to a bootstrapped folder, run `--folder <name>`.
- PASS: new `[YYMMDD]` bullets appear only for the new note; bullet count did not decrease; master watermark advanced to the new note's date; no other folder touched.

## 3. Guard: no evidence loss
- PASS: any run where the model output would reduce the `- [YYMMDD]` bullet count is rejected (check trigger.log for `REJECT`), file unchanged, watermark unchanged.

## 4. Guard: master cap
- PASS: master over 90 lines is rejected; 60-90 lines logs a WARNING but is accepted.

## 5. Resume after interruption
- Interrupt a bootstrap mid-run (Ctrl-C between batches). Re-run the same command.
- PASS: processing continues from the state.json watermark; no duplicate batches processed.

## 6. Safety: raw notes untouched
- PASS: after any run, `git status` shows no modification to any `YYMMDD-*.md` file; `Templates`, `~archive`, `~empty`, `daily-log`, and any convo subfolder contain no `_memory-*.md` files.

## 7. Lock
- Start two runs simultaneously.
- PASS: the second exits immediately with "Another convo-memory run is in progress".

## 8. Read-path smoke test
- Start a session with `>><topic>` for a bootstrapped folder.
- PASS: the session reads `_memory-master.md` + only post-watermark notes; a question whose answer lives in an old note is answered correctly (via master or index drill-down).
