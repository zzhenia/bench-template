# Cursor setup kit

The Cursor half of the per-project window setup. The Warp half lives in
`config/warp/`; this folder mirrors it feature-for-feature so a project looks
and behaves the same in either host.

The shell side — `bench_claude_named`, `bench`, `bench_menu_once` — is shared and
still lives in `config/warp/zshrc-picker.zsh`. Nothing here duplicates it.

## Contents

| File | What it is |
|------|------------|
| `cw` | Executable — opens a project in a Cursor window rooted at that folder. Install to `~/.local/bin/` |
| `sync-projects.sh` | Writes `.vscode/tasks.json` (Claude on window open) into each project. Idempotent; re-run after editing its `PROJECTS` map |

## What maps to what

| Warp | Cursor | Note |
|------|--------|------|
| `wp <name>` | `cw <name>` | Same menu, same numbers, same fuzzy matching |
| `warp://action/new_window?path=…` | `cursor <dir>` | Cursor's explorer root **is** the folder you opened, so the whole URI workaround is unnecessary |
| tab_config `color` | *(nothing)* | Deliberately not replicated — see below |
| tab_config `commands` | `.vscode/tasks.json` → `runOn: folderOpen` | The only supported "run this when the window opens" hook |
| `Cmd+/` → project explorer | `Cmd+B` | Already bound by default; deliberately not remapped, since `Cmd+/` is comment-toggle |

## Why `cw` and not `cp`

`~/.local/bin` sits ahead of `/bin` on `$PATH`, so a script named `cp` would
shadow the real copy command for every shell and every script on the machine.

## No project colours — don't add them back

A per-project window colour was built and removed the same day.
Warp's tab colours do map cleanly onto Cursor (`workbench.colorCustomizations`
in a workspace `settings.json`, tinting `statusBar` / `activityBar` /
`titleBar`, plus `window.titleBarStyle: "custom"` because a native macOS title
bar ignores `titleBar.activeBackground`). It worked, and a tinted window frame
turned out to be more distracting than useful. Reverted, and the setting was
taken back out of Cursor's user `settings.json`. Add it back only knowingly.

## Adding a project

Append a `path::mode` line to `PROJECTS` in `sync-projects.sh` and re-run it.
`mode` is `claude` (start `bench_claude_named <folder>`), `bench` (show the
picker — what the bench itself wants), or `none`.

## The one setting this depends on

`"task.allowAutomaticTasks": "on"` in Cursor's user `settings.json` — without
it Cursor asks for permission before every folderOpen task, which defeats the
point.

Each repo also needs to be **trusted** once ("Yes, I trust the authors"), or
folderOpen tasks stay disabled for it.

## The double-launch trap

`bench_menu_once` (the `.zshrc` precmd hook) already auto-starts Claude in a
Cursor terminal at a project root. The folderOpen task does the same thing, so
without a guard, opening a window and then hitting `` Ctrl+` `` would give two
Claude sessions. The task sets `BENCH_NO_MENU=1`, which `bench_should_hook` honours —
the same problem Warp solves with `bench_warp_tab_config_here`.

## Apply on a new machine

1. `install -m 755 cw ~/.local/bin/cw` — no edits needed, it discovers every
   git repo two levels under `~/dev`.
2. In Cursor: `Cmd+Shift+P` → *Shell Command: Install 'cursor' command in PATH*.
3. Edit the `PROJECTS` map in `sync-projects.sh` for this machine, then run it.
   It adds `.vscode/` to each repo's `.gitignore` (editor prefs are local) and
   backs up any pre-existing `.vscode` file it did not write to `_oldNN`.
4. Merge `"task.allowAutomaticTasks": "on"` into
   `~/Library/Application Support/Cursor/User/settings.json`, backing up to
   `settings.json_oldNN` first.
