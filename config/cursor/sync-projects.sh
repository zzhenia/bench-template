#!/usr/bin/env zsh
# ---------------------------------------------------------------------------
# sync-projects.sh — write the per-project Cursor config into each repo's
# .vscode/, the way Warp's tab_configs/*.toml do the same job for Warp.
#
# Canonical copy: <bench>/config/cursor/sync-projects.sh
# Run it again after editing the PROJECTS map below; it is idempotent, and any
# .vscode file it did not write itself is backed up to <name>_oldNN first.
#
# Each project gets one file:
#
#   .vscode/tasks.json     — a folderOpen task, the only supported way to make
#                            something run when a window opens. It launches an
#                            interactive login zsh so ~/.zshrc is sourced, then
#                            runs bench_claude_named (or `bench` for the bench,
#                            which wants the picker, not a named session).
#                            BENCH_NO_MENU=1 is set because bench_menu_once would
#                            otherwise fire in that same terminal and start
#                            Claude twice — the exact double-launch the Warp
#                            side avoids with bench_warp_tab_config_here.
#
# Deliberately NOT here: a per-project window colour. It worked (the Warp tab
# colours mapped onto statusBar/activityBar/titleBar via
# workbench.colorCustomizations) but it was tried and rejected — a tinted window
# frame is more distracting than useful. Left out on purpose; if you want it,
# add it knowingly rather than as a "missing feature".
#
# The folderOpen task needs the workspace trusted and automatic tasks allowed;
# "task.allowAutomaticTasks": "on" in Cursor's user settings.json covers the
# second, and the first is a one-time "Yes, I trust the authors" per repo.
# ---------------------------------------------------------------------------
emulate -L zsh
setopt no_nomatch

typeset -g DEV=${CW_DEV:-$HOME/dev}

# folder path :: launch mode (claude | bench | none)
typeset -a PROJECTS
# PER-MACHINE: edit this list. Paths are absolute; `$DEV` is ~/dev by default.
PROJECTS=(
  "$DEV/my-org/my-bench::bench"          # the bench wants the picker, not a named session
  "$DEV/my-org/some-project::claude"
)

# Never clobber a file we did not write. Same rule as the .zshrc/_oldNN
# backups: glob for the highest existing index and take the next one.
backup_if_foreign() {
  local f=$1 n=1 candidate
  [[ -f $f ]] || return 0
  grep -q 'config/cursor/sync-projects.sh' "$f" && return 0
  while candidate=$(printf '%s_old%02d' "$f" $n); [[ -e $candidate ]]; do (( n++ )); done
  cp "$f" "$candidate"
  print -r -- "    backed up $(basename $f) → $(basename $candidate)"
}

write_tasks() {
  local dir=$1 mode=$2 name=${1:t} cmd label
  case $mode in
    claude) cmd="bench_claude_named ${(qq)name}"; label="Claude — $name" ;;
    bench)  cmd="bench";                       label="Bench picker" ;;
    *)      return 0 ;;
  esac
  backup_if_foreign "$dir/.vscode/tasks.json"
  cat > "$dir/.vscode/tasks.json" <<JSON
{
  // Written by config/cursor/sync-projects.sh — re-run it, don't hand-edit.
  // runOn: folderOpen is Cursor's only hook for "do this when the window
  // opens" — the counterpart of a Warp tab_config's \`commands\`.
  // -il so ~/.zshrc is sourced (bench_claude_named lives there); BENCH_NO_MENU=1 so
  // the precmd hook does not launch a second Claude in this same terminal.
  "version": "2.0.0",
  "tasks": [
    {
      "label": "$label",
      "type": "shell",
      "command": "$cmd",
      "options": {
        "cwd": "\${workspaceFolder}",
        "shell": { "executable": "/bin/zsh", "args": ["-il", "-c"] },
        "env": { "BENCH_NO_MENU": "1" }
      },
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "focus": true,
        "clear": true,
        "echo": false
      },
      "runOptions": { "runOn": "folderOpen" },
      "problemMatcher": []
    }
  ]
}
JSON
}

# Editor prefs are machine-local; without this they show up as untracked noise
# in every `git status` for these repos (and would ship in bench-template).
ignore_vscode() {
  local dir=$1
  [[ -d $dir/.git ]] || return 0
  grep -qE '^\.vscode/?$' "$dir/.gitignore" 2>/dev/null && return 0
  [[ -f $dir/.gitignore && -n $(tail -c 1 "$dir/.gitignore") ]] && print -r -- "" >> "$dir/.gitignore"
  print -r -- ".vscode/" >> "$dir/.gitignore"
  print -r -- "    added .vscode/ to .gitignore"
}

for entry in $PROJECTS; do
  dir=${entry%%::*}
  mode=${entry##*::}
  if [[ ! -d $dir ]]; then
    print -r -- "  skip  ${dir:t} — no such directory"
    continue
  fi
  print -r -- "  ${dir:t}  ($mode)"
  mkdir -p "$dir/.vscode"
  write_tasks   "$dir" "$mode"
  ignore_vscode "$dir"
done

print -r -- ""
print -r -- "Done. Reopen each window for the folderOpen task to take."
