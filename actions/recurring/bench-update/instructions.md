# Bench update

Keeps a bench made from the template current with
`github.com/zzhenia/bench-template`.

- **Check (automatic).** When a Claude session starts, `check.sh` looks at GitHub
  once a day. If the template has new changes it shows "Bench update: N new
  change(s) … Type /update". Nothing shows when you are up to date. If GitHub
  can't be reached it stays quiet for three days, then warns once a day until
  it gets through.
- **Apply (`/update`).** `update.sh` applies the template's new changes as one
  commit. Your `convos/`, `config/keys.env`, `config/bench.env` and
  `.claude/settings.local.json` are never touched. When a file you changed was
  also changed upstream, Claude merges the two; if that needs your judgement it
  undoes the update and tells you which files and why.
- `config/bench-upstream` records the template version last applied.
