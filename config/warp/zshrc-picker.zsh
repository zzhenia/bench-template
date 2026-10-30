# ---------------------------------------------------------------------------
# Project picker + convo launcher — Warp, Zed, Cursor  (canonical: config/warp/)
#
# Append this block to ~/.zshrc (back it up first: ~/.zshrc_oldNN, glob for
# existing _old* and use the next number). Then edit the two PER-MACHINE
# sections below.
#
# What it does on every new Warp tab / Zed or Cursor terminal opened in the bench:
#   - opens straight on the convo picker (needs a bench checkout): pick or
#     type a convo name once and it fans out to `-n <name>`, /color <random>,
#     and a staged-but-unsent ">>name" first message (zero tokens until Enter)
#   - `r` + Enter there opens a one-keystroke project menu, cds to the pick, launches
#     Claude Code with --model opus --permission-mode auto
#   - `s` + Enter, a blank line, or 30s of silence -> plain shell
#   - `bench` reopens the menu any time; `convo <name>` jumps straight in
#
# In **Zed and Cursor only**, a terminal opened at one of the other BENCH_PROJECTS
# roots skips the menu and starts Claude renamed to that project (2s any-key
# bail). Neither editor has terminal tab colours or a tab-config equivalent, so
# the directory is the trigger; on Warp the same job is done by
# ~/.warp/tab_configs/*.toml, and the gate below keeps the two from both firing
# in one tab.
#
# Why a precmd hook and not code at the end of .zshrc: Warp sources rcfiles
# FIRST and registers its shell integration last, so anything blocking here
# would run mid-handshake. Gating on $WARP_BOOTSTRAPPED means the menu can
# only appear once Warp is fully up. Zed and Cursor have no such handshake and
# only need the precmd deferral.
#
# Requirements: zsh, Warp/Zed/Cursor, Claude Code on PATH, expect (ships with macOS).
# Escape hatches: BENCH_NO_MENU=1 disables the menu entirely.
# Injection gotchas encoded below (do not "simplify" them away):
#   - commands are sent as one instant burst = paste, so Claude's slash-command
#     menu never opens; typed char-by-char the menu fuzzy-matches and hijacks
#     Enter onto a recently used command (observed: /color ran /note)
#   - \r goes as a separate later keystroke; inside a burst it becomes a
#     newline in the input box and nothing submits
# ---------------------------------------------------------------------------

# --- PER-MACHINE: project list (menu digits, in order) ----------------------
typeset -ga BENCH_PROJECTS=(
  "$HOME/dev/my-org/my-bench"
  "$HOME/dev/my-org/example-project"
  "$HOME/dev/my-org/my project"
)
# --- PER-MACHINE: bench checkout (convo picker hides itself if missing) -----
typeset -g BENCH_DIR="$HOME/dev/my-org/my-bench"

typeset -ga BENCH_COLORS=(red blue green yellow purple orange pink cyan)

# Every picker launch: auto mode + Opus.
# BENCH_CLAUDE_BIN overrides the binary (used by the pty test harness).
bench_claude() {
  local bin=${BENCH_CLAUDE_BIN:-claude}
  if command -v -- "$bin" >/dev/null 2>&1; then
    "$bin" --model opus --permission-mode auto "$@"
  else
    print -r -- "  claude not on PATH"
    return 1
  fi
}

convo() {
  emulate -L zsh
  local name=$1 line i color
  local -a recent
  if [[ ! -d $BENCH_DIR/convos ]]; then
    print -r -- "  no bench checkout at $BENCH_DIR"
    return 1
  fi
  if [[ -z $name ]]; then
    recent=( "$BENCH_DIR"/convos/[a-zA-Z0-9]*(/Nom[1,24]) )
    print -r -- ""
    for (( i = 1; i <= ${#recent[@]}; i++ )); do
      printf "  %2d  %-26s" $i "${recent[$i]:t}"
      (( i % 3 == 0 )) && print
    done
    (( ${#recent[@]} % 3 )) && print
    print -r -- ""
    print -r -- "   r⏎ other repo…              s⏎ just a shell"
    [[ -f $BENCH_DIR/tools/on-demand/catchup/catchup.py ]] \
      && print -r -- "   c⏎ catch up (convos since last run)"
    print -r -- ""
    local prompt="  pick (number, or type a name + Enter): " key
    print -n -- "$prompt"
    if ! read -s -k 1 -t 30 key; then
      print -r -- "— no pick, plain shell (run \`bench\` for the menu)"
      return 0
    fi
    case $key in
      $'\n'|$'\r'|' ') print -r -- "shell"; return 0 ;;
    esac
    line=$key
    if [[ $key == <-> ]]; then
      # A digit launches at once, unless it could still start a listed
      # two-digit number (1 -> 1x with 10+ convos): then 0.7s for a second one.
      if (( key * 10 <= ${#recent[@]} )) && read -s -k 1 -t 0.7 key \
         && [[ $key == <-> ]]; then
        line+=$key
      fi
    else
      # Any other key starts a convo name: finish it in a line editor.
      print -n -- "\r"
      vared -p "$prompt" line || return 0
      # A lone r / s / c + Enter is a menu action; anything longer is a convo
      # name, so convos starting with those letters can still be typed.
      case $line in
        [rR]) bench_repo_menu; return $? ;;
        [sS]|'') print -r -- "  shell"; return 0 ;;
        [cC]) if [[ -f $BENCH_DIR/tools/on-demand/catchup/catchup.py ]]; then
                cd -- "$BENCH_DIR" || return 1
                bench_claude -n "Catchup" "catchup"
                return $?
              fi ;;
      esac
    fi
    if [[ $line == <-> ]] && (( line >= 1 && line <= ${#recent[@]} )); then
      name=${recent[$line]:t}
      print -r -- "  ${name}"
    else
      name=$line
    fi
  fi
  name=${name:l}
  name=${name// /-}
  name=${name//[^a-z0-9-]/}
  [[ -n $name ]] || return 0
  color=${BENCH_COLORS[$(( RANDOM % ${#BENCH_COLORS[@]} + 1 ))]}
  cd -- "$BENCH_DIR" || return 1

  if ! command -v expect >/dev/null 2>&1; then
    bench_claude ">>$name "
    return $?
  fi

  local bench_tty; bench_tty=$(stty -g 2>/dev/null)
  BENCH_CONVO_NAME=$name BENCH_CONVO_COLOR=$color \
    BENCH_CONVO_BIN=${BENCH_CLAUDE_BIN:-claude} expect -f =(cat <<'EXPECT_EOF'
set name  $env(BENCH_CONVO_NAME)
set color $env(BENCH_CONVO_COLOR)
set timeout 25
# Claude's TUI switches on mouse-motion (DECSET 1003/1006) and focus reporting
# (1004) the instant it starts. Until interact() takes the real terminal into
# raw mode, those reports arrive on a tty that still has echo on, so every
# mouse twitch paints ^[[<35;x;yM and ^[[I across the screen before the
# prompt. Echo off for the scripted phase;
# interact sets raw mode itself and expect restores the saved modes on exit.
catch {stty -echo}
spawn -noecho $env(BENCH_CONVO_BIN) --model opus --permission-mode auto -n $name
# Match the spawned pty to the real terminal, now and on every resize.
proc syncsize {} {
  global spawn_out
  set d [stty size]
  stty rows [lindex $d 0] columns [lindex $d 1] < $spawn_out(slave,name)
}
syncsize
trap syncsize WINCH
# `-n` sets the session name natively, so nothing is typed for it. Every
# synthetic burst races Claude's startup, and keys that land too early get
# eaten by whatever dialog is still on screen — that is how sessions kept
# coming up in manual mode instead of auto, and how stray ^[[200~ ended up in
# the input box. Claude Code ≥ 2.1 dropped "shift+tab" from the footer.
# Match the header text instead — it renders once the TUI is up and the
# input box is ready. 6s fallback keeps worst-case under 8s (was 36s).
expect {
  -timeout 6 "Claude" {}
  timeout {}
}
sleep 0.5
send -- "/color $color"
sleep 0.3
send -- "\r"
expect {
  -timeout 3 -re {set.{0,40}to:} {}
  timeout {}
}
sleep 0.4
# Trailing space: the staged text sits in Claude's input box and whatever
# the user types lands right after it, so without the space the first word
# collides with the convo name (">>spanish-studyWhen I run…").
send -- ">>$name "
interact
EXPECT_EOF
)
  local rc=$?
  # Safety net: if expect dies before interact restores the tty, the shell would
  # be left with echo off and look dead. Put the saved modes back either way.
  [[ -n $bench_tty ]] && stty "$bench_tty" 2>/dev/null
  return $rc
}

# The new-tab picker: bench convos first (`r` there opens the repo menu below).
bench() {
  if [[ -d $BENCH_DIR/convos ]]; then
    convo
  else
    bench_repo_menu
  fi
}

bench_repo_menu() {
  local i key dir
  print -r -- ""
  for (( i = 1; i <= ${#BENCH_PROJECTS[@]}; i++ )); do
    print -r -- "  $i  ${BENCH_PROJECTS[$i]:t}"
  done
  print -r -- "  s  just a shell"
  print -r -- ""
  print -n -- "  pick: "

  if ! read -s -k 1 -t 30 key; then
    print -r -- "— no pick, plain shell (run \`bench\` for the menu)"
    return 0
  fi

  # A digit in range picks a project; anything else (s, Enter, …) is a shell.
  if [[ $key != <-> ]] || (( key < 1 || key > ${#BENCH_PROJECTS[@]} )); then
    print -r -- "shell"
    return 0
  fi

  dir=${BENCH_PROJECTS[$key]}
  print -r -- "${dir:t}"

  if [[ ! -d $dir ]]; then
    print -r -- "  missing: $dir"
    return 1
  fi

  # An editor's file tree belongs to the WINDOW, not the shell — cd'ing here
  # starts Claude in the right place but leaves the tree on whatever folder the
  # window was opened with. So in Cursor a pick opens a new window rooted at
  # that repo: its terminal comes up at a project root, which is exactly what
  # bench_menu_once auto-launches Claude from, renamed to the project. This shell
  # is left as a plain shell. Skipped when the window is already rooted at the
  # pick (that would just duplicate the window) and when the CLI is missing.
  if [[ $BENCH_TERM_KIND == cursor && $dir != "$BENCH_WORKSPACE_ROOT" ]] \
     && command -v cursor >/dev/null 2>&1; then
    print -r -- "  opening ${dir:t} in a new Cursor window…"
    # -u BENCH_MENU_DONE: belt and braces. The tty comparison in bench_should_hook
    # already survives inheritance, but the new window has no business
    # carrying this shell's marker at all.
    (env -u BENCH_MENU_DONE cursor -n "$dir" >/dev/null 2>&1 &)
    return 0
  fi

  cd -- "$dir" || return 1

  bench_claude
}

# Launch Claude in the current directory under the session name $1.
# Tab configs carry a `title`, but Claude Code takes ownership of the tab title
# the instant its TUI starts, so that title survives only milliseconds — the
# name has to be set inside Claude. `claude -n <name>` does exactly that (it
# feeds the prompt box, the /resume picker and the terminal title), so expect is
# left with only the random /color to type. No staged >> message here — these
# are project tabs, not convos. Falls back to a plain launch if expect is
# missing or no name was given.
bench_claude_named() {
  emulate -L zsh
  local name=$1 color
  if [[ -z $name ]] || ! command -v expect >/dev/null 2>&1; then
    bench_claude
    return $?
  fi

  # Random session colour, same as convo(). This is Claude Code's own session
  # colour, not the Warp tab colour — the two are independent, so a tab config's
  # static `color` still owns the tab and nothing here overrides it.
  color=${BENCH_COLORS[$(( RANDOM % ${#BENCH_COLORS[@]} + 1 ))]}

  local bench_tty; bench_tty=$(stty -g 2>/dev/null)
  BENCH_RENAME_NAME=$name BENCH_RENAME_COLOR=$color BENCH_RENAME_BIN=${BENCH_CLAUDE_BIN:-claude} expect -f =(cat <<'EXPECT_EOF'
set name $env(BENCH_RENAME_NAME)
set color $env(BENCH_RENAME_COLOR)
set timeout 25
# Claude's TUI switches on mouse-motion (DECSET 1003/1006) and focus reporting
# (1004) the instant it starts. Until interact() takes the real terminal into
# raw mode, those reports arrive on a tty that still has echo on, so every
# mouse twitch paints ^[[<35;x;yM and ^[[I across the screen before the
# prompt. Echo off for the scripted phase;
# interact sets raw mode itself and expect restores the saved modes on exit.
catch {stty -echo}
spawn -noecho $env(BENCH_RENAME_BIN) --model opus --permission-mode auto -n $name
# Match the spawned pty to the real terminal, now and on every resize.
proc syncsize {} {
  global spawn_out
  set d [stty size]
  stty rows [lindex $d 0] columns [lindex $d 1] < $spawn_out(slave,name)
}
syncsize
trap syncsize WINCH
# Readiness: match the "Claude Code" header (renders once the input box is
# up, ~1s), then a short settle. The old rule waited for a SECOND footer
# render, which Claude ≥ 2.1 never does, so it burned its full 10s timeout;
# and the ack was matched as "color set", which Claude paints as separate
# words with cursor moves between them, so that burned 6s more (an
# 11s frozen window). The ack regex below spans those escapes. Only /color is
# typed — `-n` handles the name natively. It goes in as one instant burst so
# Claude reads it as a paste and the slash-command menu never opens, then \r
# goes separately as a real Enter (a \r inside the burst becomes a newline
# in the input box and nothing submits).
expect {
  -timeout 6 "Claude" {}
  timeout {}
}
sleep 0.5
send -- "/color $color"
sleep 0.3
send -- "\r"
expect {
  -timeout 3 -re {set.{0,40}to:} {}
  timeout {}
}
interact
EXPECT_EOF
)
  local rc=$?
  # Safety net: if expect dies before interact restores the tty, the shell would
  # be left with echo off and look dead. Put the saved modes back either way.
  [[ -n $bench_tty ]] && stty "$bench_tty" 2>/dev/null
  return $rc
}

# Which terminal is this? Warp, Zed and Cursor all get the automation, and Warp
# differs in exactly one respect: it registers its shell integration AFTER
# sourcing rcfiles ("Do other shell startup first so we can ensure Warp goes
# last"), so the menu must wait for $WARP_BOOTSTRAPPED or it runs mid-handshake
# and kills paste and the Project Explorer. Zed and
# Cursor have no such handshake, so their first precmd is safe.
#
# Keyed off TERM_PROGRAM alone, as one exclusive case. Zed also exports
# ZED_TERM=true, but that variable is inherited by every child process, so a
# Warp tab launched from inside Zed would test true for both — and the Zed
# branch below auto-launches Claude, which in a Warp tab config would launch
# it a second time. TERM_PROGRAM is re-set by whichever terminal owns the pty.
#
# Cursor is a VS Code fork and reports TERM_PROGRAM=vscode exactly like real
# VS Code, so TERM_PROGRAM alone cannot separate them. Cursor ships through
# ToDesktop (bundle id com.todesktop.*) and its git extension exports the app
# path into the terminal environment; plain VS Code matches neither and is left
# alone. Both markers are inheritable, but they are only read once TERM_PROGRAM
# is already vscode, which the owning terminal sets for itself.
typeset -g BENCH_TERM_KIND=
case $TERM_PROGRAM in
  WarpTerminal) BENCH_TERM_KIND=warp ;;
  zed)          BENCH_TERM_KIND=zed  ;;
  vscode)
    [[ $__CFBundleIdentifier == com.todesktop.* \
       || $VSCODE_GIT_ASKPASS_NODE == */Cursor.app/* ]] && BENCH_TERM_KIND=cursor
    ;;
esac

# Basename of the BENCH_PROJECTS entry whose root is $PWD; non-zero if $PWD is not
# a project root. Decides auto-launch vs. menu vs. leave-it-alone.
bench_project_here() {
  local p
  for p in "${BENCH_PROJECTS[@]}"; do
    [[ $PWD == "$p" ]] && { print -r -- "${p:t}"; return 0; }
  done
  return 1
}

# True when $PWD is a parent of a project or sits inside one, without being a
# root itself. Editors open the terminal at the workspace root, and a workspace
# is very often the containing folder (~/dev/my-org) rather than one project —
# a case that matches no root and would otherwise get silence, which reads as
# "the automation is broken". Kept deliberately narrow so unrelated repos
# opened in Cursor or Zed stay quiet.
bench_near_project() {
  local p
  for p in "${BENCH_PROJECTS[@]}"; do
    [[ $p == "$PWD"/* || $PWD == "$p"/* ]] && return 0
  done
  return 1
}

# True when a Warp tab config already covers $PWD — i.e. this window will run
# bench_claude_named itself and the hook must stay out of the way. Compared with
# spaces normalised to hyphens, because a tab config `name` must be URI-safe
# ("my-project" for the folder "my project") — see config/warp/wp.
bench_warp_tab_config_here() {
  local want=${${PWD:t:l}// /-} f n
  for f in ~/.warp/tab_configs/*.toml(N); do
    n=$(sed -n 's/^name[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$f" | head -1)
    [[ -n $n && ${${n:l}// /-} == $want ]] && return 0
  done
  return 1
}

bench_menu_once() {
  # Warp only: wait for the shell-integration handshake, retry next prompt.
  [[ $BENCH_TERM_KIND == warp && -z $WARP_BOOTSTRAPPED ]] && return 0
  add-zsh-hook -d precmd bench_menu_once

  # In the bench (or when BENCH_DIR is misconfigured — see fail-safe below),
  # show the project picker.
  if [[ $PWD == "$BENCH_DIR" || ! -d $BENCH_DIR ]]; then
    bench
    return $?
  fi

  # Zed and Cursor only, and only in another project's root: start Claude
  # renamed to that project. This stands in for Warp's coloured tab configs —
  # neither editor has terminal tab colours or a tab-config equivalent, but
  # both open terminals at the workspace root, so the directory itself is the
  # trigger. Warp must never reach here: its tab configs already run
  # bench_claude_named themselves, and firing again would launch Claude twice.
  # Warp reaches here only via `wp` (config/warp/wp) opening a plain window at
  # a repo with no tab config — bench_should_hook has already established that.
  # The folder name is the project name; no picker, no prompt.
  if [[ $BENCH_TERM_KIND == warp ]]; then
    bench_claude_named "${PWD:t}"
    return $?
  fi

  [[ $BENCH_TERM_KIND == (zed|cursor) ]] || return 0
  local proj
  if ! proj=$(bench_project_here); then
    # Not a project root. If the workspace is a parent of the projects or a
    # folder inside one, fall back to the picker; anywhere else, stay quiet.
    bench_near_project || return 0
    bench
    return $?
  fi
  print -r -- ""
  print -n -- "  Claude in ${proj} — any key for a plain shell… "
  if read -s -k 1 -t 2; then
    print -r -- "shell"
    return 0
  fi
  print -r -- ""
  bench_claude_named "$proj"
}

# Registration gate.
#
# Warp keeps its $PWD condition here: ordinary Warp tabs open in BENCH_DIR
# (settings.toml working_directory_config) while a tab config opens in its own
# project directory, so "cwd is the bench" cleanly separates the two. Tab
# configs cannot set env vars, so BENCH_NO_MENU=1 is unavailable to them and this
# is the gate that works.
#
# Zed and Cursor always register; bench_menu_once above decides what to do from
# $PWD, since in an editor a project-root terminal should auto-launch rather
# than do nothing.
#
# The `! -d $BENCH_DIR` fail-safe lives in bench_menu_once: if BENCH_DIR is
# wrong for this machine, the menu appears in every tab (annoying, visible,
# points straight at the PER-MACHINE block) rather than in none, which would
# read as "the picker broke" with nothing to blame.
#
# BENCH_MENU_DONE holds the TTY it was set on, not a bare 1. It is exported so a
# nested shell in the SAME terminal stays quiet, but an exported 1 also travels
# into anything that terminal launches — including `cursor -n`, whose new
# window can hand that environment to its own terminals, silencing the menu
# there for no visible reason. Comparing against $TTY keeps the nested-shell
# suppression while letting a genuinely new terminal fire.
bench_should_hook() {
  [[ -o interactive && -t 0 && -z $BENCH_NO_MENU && $BENCH_MENU_DONE != "$TTY" ]] || return 1
  case $BENCH_TERM_KIND in
    warp)        [[ $PWD == "$BENCH_DIR" || ! -d $BENCH_DIR ]] && return 0
                 [[ $PWD == $HOME/dev/*/* && -d $PWD/.git ]] || return 1
                 ! bench_warp_tab_config_here ;;
    zed|cursor)  return 0 ;;
    *)           return 1 ;;
  esac
}

if bench_should_hook; then
  export BENCH_MENU_DONE=$TTY
  # The folder the window was opened with: an editor spawns its terminals at
  # the workspace root, so the first prompt's cwd is that root. bench() uses it
  # to tell "pick a different repo" (new window) from "pick the one I'm already
  # in" (launch here), and it must be captured before any cd moves us.
  typeset -g BENCH_WORKSPACE_ROOT=$PWD
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd bench_menu_once
fi

# ---------------------------------------------------------------------------
# img — open a Claude Code [Image #N] attachment.
# Deliberately NOT a shell function: it lives at ~/.local/bin/img (canonical
# copy in the bench at config/warp/img) so it also works from inside Claude Code's
# TUI via `!img 23`. A function here would only exist at a shell prompt.
# ---------------------------------------------------------------------------
