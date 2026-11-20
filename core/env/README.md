# env — editor and terminal settings

One folder per environment the bench runs in. Each holds the settings the bench
needs from that app and an `env.json` naming the file they merge into.

| Folder | Merges into |
|--------|-------------|
| `cursor/` | Cursor's user `settings.json` |
| `warp/` | `~/.warp/settings.toml`, `~/.warp/keybindings.yaml` |
| `claude/` | `~/.claude/settings.json` (Claude Code, in any terminal) |

`apply.py` merges them key by key. It runs from the bench's `setup.sh` on a new
machine and from every `/update`. A missing key is added; a key the user already
set to something else is asked about (bench value, or keep theirs), and the
answer is kept in `~/.config/bench/env-choices.json` until the bench value
changes. Every changed file is backed up first as `<file>_oldNN`. An app that is
not installed is skipped.

```bash
python3 core/env/apply.py            # apply; asks in a terminal
python3 core/env/apply.py --check    # show what would change
python3 core/env/apply.py --choose cursor:<key>=bench warp:<key>=mine
```

To add a setting: put it in the env's fragment, explain it in that env's README,
publish core. Each bench picks it up on its next `/update`.
