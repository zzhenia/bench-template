# Bench update

Keeps a bench current with the bench template named by `BENCH_UPSTREAM_URL` in
`config/bench.env`. A bench without that line takes no updates.

- **Check (automatic).** When a Claude session starts, `check.sh` looks at the
  template once a day. If it has new changes it shows "Bench update: N new
  change(s) … Type /update". Nothing shows when you are up to date. If the
  template can't be reached it stays quiet for three days, then warns once a
  day until it gets through.
- **Apply (`/update`).** `update.sh` applies the template's new changes as one
  commit, then relinks skills (`core/bin/link-skills.sh`). Your `convos/`,
  `personal/`, `config/keys.env`, `config/bench.env` and
  `.claude/settings.local.json` are never touched. When a file you changed was
  also changed upstream, Claude merges the two; if that needs your judgement it
  undoes the update and tells you which files and why.
- **Core only.** `BENCH_UPDATE_SCOPE=core` in `config/bench.env` limits updates
  to `core/`, for a bench that was not made from the template.
- `config/bench-upstream` records the template version last applied.
