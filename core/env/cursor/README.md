# Cursor setup kit

The Cursor half of the per-project window setup. The Warp half lives in
`core/env/warp/`; this folder mirrors it feature-for-feature so a project looks and behaves the
same in either app.

The shell side — `bench_claude_named`, `bench`, `bench_menu_once` — is shared
and lives in `core/shell/bench.zsh`, with `cw` and `sync-projects.sh` beside it.
Nothing here duplicates it.

## Contents

| File | What it is |
|------|------------|
| `settings.json` | Cursor settings the bench needs, merged into Cursor's user `settings.json` by `core/env/apply.py` |
| `core/shell/cw` | Executable — opens a project in a Cursor window rooted at that folder. Symlink into `~/.local/bin/` |
| `core/shell/sync-projects.sh` | Writes `.vscode/tasks.json` (Claude on window open) into each project in `config/projects.tsv`. Idempotent; re-run after editing that file |

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

A per-project window colour was built once and removed the same day.
Warp's tab colours do map cleanly onto Cursor (`workbench.colorCustomizations`
in a workspace `settings.json`, tinting `statusBar` / `activityBar` /
`titleBar`, plus `window.titleBarStyle: "custom"` because a native macOS title
bar ignores `titleBar.activeBackground`). It worked, and a cyan
window frame was not wanted. Reverted, and the setting was taken back out
of Cursor's user `settings.json`.

## Adding a project

Add a `path<TAB>mode` line to `config/projects.tsv` and re-run
`core/shell/sync-projects.sh`. `mode` is `claude` (start `bench_claude_named <folder>`), `bench` (show the
picker — what the bench itself wants), or `none`.

## The one setting this depends on

`"task.allowAutomaticTasks": "on"` in Cursor's user `settings.json` — without it Cursor asks for permission before every folderOpen task,
which defeats the point.

Each repo also needs to be **trusted** once ("Yes, I trust the authors"), or
folderOpen tasks stay disabled for it.

## Terminal tab names

`"terminal.integrated.tabs.title": "${sequence}"` (`settings.json`). Cursor's default is `${process}`, the name of the foreground binary —
which reads **`expect`**, because `convo` and `bench_claude_named` drive Claude
through an expect wrapper. `${sequence}` uses the title Claude Code emits
itself, so a session started as `claude -n the-bench` labels its tab
`✳ the-bench`, and `/rename` inside the session retitles it live.
`"terminal.integrated.tabs.description": ""` drops the trailing cwd noise.

Warp needs none of this: a tab config's `title` plus Claude's own OSC-0 title
already name the tab.

## No locked editor groups

`"workbench.editor.autoLockGroups": { "terminalEditor": false,
"vscode.markdown.preview.editor": false }` (`settings.json`).

Cursor locks any group holding a terminal or a Markdown preview so that opening
a file can never take that group over — the new editor is pushed into a
different group instead. Because `defaultLocation: editor` makes terminals the
main editor tabs, that padlock was showing on essentially every tab. Turning it
off for those two editor kinds is the trade chosen: a file opened
while a Claude tab is focused can now land in that group and cover the session.
Everything else keeps VS Code's defaults.

## No exit-code toasts

`"terminal.integrated.showExitAlert": false` (user `settings.json`). Auto-note
closes an idle tab by killing its shell, and Cursor answered each one with a
"terminal process terminated with exit code: 1" toast that offered nothing to
undo.

## The double-launch trap

`bench_menu_once` (the `.zshrc` precmd hook) already auto-starts Claude in a
Cursor terminal at a project root. The folderOpen task does the same thing, so
without a guard, opening a window and then hitting `` Ctrl+` `` would give two
Claude sessions. The task sets `BENCH_NO_MENU=1`, which `bench_should_hook` honours —
the same problem Warp solves with `bench_warp_tab_config_here`.

## Apply on a new machine

1. `ln -s <bench>/core/shell/cw ~/.local/bin/cw` — no edits needed, it
   discovers every git repo two levels under `BENCH_DEV_DIR`.
2. In Cursor: `Cmd+Shift+P` → *Shell Command: Install 'cursor' command in PATH*.
3. Edit `config/projects.tsv` for this machine, then run `core/shell/sync-projects.sh`.
   It adds `.vscode/` to each repo's `.gitignore` (editor prefs are local) and
   backs up any pre-existing `.vscode` file it did not write to `_oldNN`.
4. `python3 core/env/apply.py` — merges `settings.json` into Cursor's, backing it up
   first; asks before changing a value you set yourself.
5. `cursor --install-extension svsool.markdown-memo` — Markdown Memo makes
   Obsidian-style `[[Note | alias]]` wikilinks clickable in the Markdown
   preview and the editor (the built-in preview ignores them). Needed for
   the Slipbox and any SMKS vault opened in Cursor.
