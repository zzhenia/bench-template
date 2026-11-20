# core/shell — the terminal layer

What runs on every new terminal in **Warp** and **Cursor**: the convo picker in
the bench, a named Claude Code session in other projects, and the `wp` / `cw`
window openers. A plain terminal still runs Claude Code fine; it just gets none
of this.

| File | What it is |
|---|---|
| `bench.zsh` | Sourced from `~/.zshrc`. Defines `bench`, `convo`, `bench_claude`, `bench_claude_named`, `bench_repo_menu` and the precmd hook `bench_menu_once`. Old `zv_*` names are kept as wrappers |
| `lib.zsh` | Finds the bench root and reads `config/bench.env` and `config/projects.tsv` (no forks; runs on every terminal) |
| `wp` | Opens a project in a new Warp window (`warp://…?new_window=true`, the only way to set the Project Explorer root) |
| `cw` | Opens a project in a Cursor window (`cursor <dir>`) |
| `sync-projects.sh` | Writes each project's `.vscode/tasks.json` (a `runOn: folderOpen` task) from `config/projects.tsv` |

## Install

```sh
# ~/.zshrc (back it up first, ~/.zshrc_oldNN)
source "<bench>/core/shell/bench.zsh"

ln -s <bench>/core/shell/wp ~/.local/bin/wp
ln -s <bench>/core/shell/cw ~/.local/bin/cw
<bench>/core/shell/sync-projects.sh        # Cursor only; re-run after editing projects.tsv
zsh -i -c 'type bench; type bench_claude_named'
```

Needs zsh, Claude Code on `PATH`, and `expect` (ships with macOS).

## This bench's values

`config/projects.tsv` — one project per line, `path<TAB>mode`, in menu order.
A path may start with `~` or be relative to the bench (`.` is the bench).
`mode` is what the Cursor folderOpen task runs: `bench` (the picker),
`claude` (`bench_claude_named <folder>`), or `none`.

`config/bench.env`:

| Key | Default | Meaning |
|---|---|---|
| `BENCH_DEV_DIR` | `~/dev` | `wp`/`cw` list every git repo two levels below it; the Warp hook accepts repos there |
| `BENCH_OTHER_WINDOW` | — | A second bench, offered as `0` in the picker; opens in its own Cursor window |
| `BENCH_OTHER_WINDOW_LABEL` | `other bench` | Its label in the picker |
| `BENCH_CATCHUP_QUEUE` | `~/.bench-catchup` | Folder a catch-up tool drops new-tab briefs into; the first prompt claims one |

Environment (each also accepted with the older `ZV_` prefix):
`BENCH_NO_MENU=1` turns the hook off; `BENCH_WINDOW_BENCH` points a window's
picker at another bench and `BENCH_CONVO_GLOB` filters its convos (set both in a
workspace's `terminal.integrated.env.osx`); `BENCH_CLAUDE_BIN` swaps the binary
(test harness); `BENCH_CLAUDE_DEBUG=1` adds `--debug-file` for one launch.

## Warp and Cursor differ on purpose

| Concern | Warp | Cursor |
|---|---|---|
| Open a project in its own window | `wp <name>` | `cw <name>` |
| Run something on window open | `~/.warp/tab_configs/*.toml` → `commands` | `<repo>/.vscode/tasks.json` → `runOn: folderOpen` |
| What stops a double Claude launch | `bench_warp_tab_config_here`: the hook stays out of tabs a tab config covers | the task sets `BENCH_NO_MENU=1` |
| When the hook may run | after `$WARP_BOOTSTRAPPED` (Warp registers its integration after rcfiles) | first prompt |

When you change `bench.zsh`, check both arms.

## Rules encoded in the expect scripts

- Commands go in as one instant burst (a paste), so Claude's slash-command menu
  never opens; `\r` goes separately, or it becomes a newline and nothing submits.
- Echo is off until `interact`, so mouse/focus reports don't paint the screen.
- A session ending its reply with `ZVBYE` (the `/e` skill) gets a real `/exit`;
  after Claude exits, `core/tools/auto-note/auto_note.py --exit <pid>` writes
  the note and the tab closes.
