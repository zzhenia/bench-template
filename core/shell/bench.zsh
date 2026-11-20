# ---------------------------------------------------------------------------
# Bench terminal layer — project picker + convo launcher for Warp and Cursor
# (Zed works the same way; it is legacy and not extended).
#
# Install: one line in ~/.zshrc (back it up first, ~/.zshrc_oldNN):
#   source "<bench>/core/shell/bench.zsh"
# Per-bench values come from the bench, not from this file:
#   config/projects.tsv  project list (menu digits, in order) + Cursor launch mode
#   config/bench.env     BENCH_DEV_DIR, BENCH_OTHER_WINDOW(_LABEL), BENCH_CATCHUP_QUEUE
# See core/shell/README.md.
#
# What it does on every new Warp tab / Cursor terminal opened in the bench:
#   - opens straight on the convo picker: pick or type a convo name once and it
#     fans out to `-n <name>`, /color <random>, and a staged-but-unsent ">>name"
#     first message (zero tokens until Enter)
#   - `r` + Enter there opens a one-keystroke project menu, cds to the pick,
#     launches Claude Code with --permission-mode auto
#   - `s` + Enter, a blank line, or 30s of silence -> plain shell
#   - `bench` reopens the menu any time; `convo <name>` jumps straight in
#
# In Cursor (and Zed) only, a terminal opened at one of the other projects'
# roots skips the menu and starts Claude named after that project (2s any-key
# bail). Neither editor has terminal tab colours or a tab-config equivalent, so
# the directory is the trigger; on Warp the same job is done by
# ~/.warp/tab_configs/*.toml, and the gate below keeps the two from both firing.
#
# Why a precmd hook and not code at the end of .zshrc: Warp sources rcfiles
# FIRST and registers its shell integration last, so anything blocking here
# would run mid-handshake. Gating on $WARP_BOOTSTRAPPED means the menu can only
# appear once Warp is fully up. Cursor has no such handshake and only needs the
# precmd deferral.
#
# Names: functions are bench_*; the older zv_* names are kept as wrappers at the
# end of this file, and every ZV_* environment input is still honoured.
#
# Requirements: zsh, Claude Code on PATH, expect (ships with macOS).
# Escape hatch: BENCH_NO_MENU=1 (or ZV_NO_MENU=1) disables the menu entirely.
# Injection gotchas encoded below (do not "simplify" them away):
#   - commands are sent as one instant burst = paste, so Claude's slash-command
#     menu never opens; typed char-by-char the menu fuzzy-matches and hijacks
#     Enter onto a recently used command (observed: /color ran /note)
#   - \r goes as a separate later keystroke; inside a burst it becomes a
#     newline in the input box and nothing submits
# ---------------------------------------------------------------------------

source "${${(%):-%x}:A:h}/lib.zsh"
bench_shell_init "${${(%):-%x}:A:h:h:h}"

# The bench whose convos the picker lists. A window can point it at another
# bench: its workspace settings set BENCH_WINDOW_BENCH (or ZV_WINDOW_BENCH), and
# BENCH_CONVO_GLOB (or ZV_CONVO_GLOB) to show only some convos, in
# terminal.integrated.env.osx. Shared scripts (auto-note) always come from
# BENCH_HOME, the bench this file lives in.
typeset -g BENCH_WINDOW=${BENCH_WINDOW_BENCH:-$ZV_WINDOW_BENCH}
typeset -g BENCH_DIR=${BENCH_WINDOW:-$BENCH_HOME}
typeset -g BENCH_CONVO_GLOB=${BENCH_CONVO_GLOB:-$ZV_CONVO_GLOB}
bench_cfg BENCH_DEV_DIR "$HOME/dev";              typeset -g BENCH_DEV=$REPLY
bench_cfg BENCH_OTHER_WINDOW;                     typeset -g BENCH_OTHER_WINDOW=$REPLY
bench_cfg BENCH_OTHER_WINDOW_LABEL "other bench"; typeset -g BENCH_OTHER_WINDOW_LABEL=$REPLY
bench_cfg BENCH_CATCHUP_QUEUE "$HOME/.bench-catchup"; typeset -g BENCH_CATCHUP_QUEUE=$REPLY

typeset -g BENCH_AI=claude   # claude | deepseek — chosen by bench_choose_ai below

# Backend choice: 1 Claude, 2 DeepSeek (the same Claude Code, run on
# DeepSeek — see bench_ai_export). Parked: bench() does not call it, so every
# picker launch is Claude. Call it before convo/bench_repo_menu to bring it back.
bench_choose_ai() {
  local key
  print -r -- ""
  print -r -- "  1  Claude"
  print -r -- "  2  DeepSeek"
  print -r -- "  s  just a shell"
  print -r -- ""
  print -n -- "  pick: "
  if ! read -s -k 1 -t 30 key; then
    print -r -- "— no pick, plain shell"
    return 1
  fi
  case $key in
    1) BENCH_AI=claude;   print -r -- "Claude";   return 0 ;;
    2) BENCH_AI=deepseek; print -r -- "DeepSeek"; return 0 ;;
    *) print -r -- "shell"; return 1 ;;
  esac
}

# DeepSeek is the same Claude Code window, pointed at DeepSeek's Anthropic-
# compatible API. Models and key come from the bench's AI profile
# (scripts/bench-profile env deepseek). Call it inside a ( subshell ) around the
# launch, so the exports die with the session and this shell keeps the
# claude.ai login. No-op for Claude.
bench_ai_export() {
  [[ $BENCH_AI == deepseek ]] || return 0
  local lines
  if ! lines=$(python3 "$BENCH_DIR/scripts/bench-profile" env deepseek); then
    print -r -- "  DeepSeek settings unavailable (scripts/bench-profile env deepseek)"
    return 1
  fi
  eval "$lines"
}

typeset -ga BENCH_COLORS=(red blue green yellow purple orange pink cyan)

# Every picker launch: auto mode.
# BENCH_CLAUDE_BIN (or ZV_CLAUDE_BIN) overrides the binary (pty test harness).
# No --debug-file: `claude --help` says it "implicitly enables debug mode",
# which slows startup, prints extra chatter, and writes every command Claude
# runs — credentials included — into a log. BENCH_CLAUDE_DEBUG=1 (or
# ZV_CLAUDE_DEBUG=1) turns it back on for one launch when actually needed.
bench_claude() {
  local bin=${BENCH_CLAUDE_BIN:-${ZV_CLAUDE_BIN:-claude}}
  local -a dbg=()
  [[ -n ${BENCH_CLAUDE_DEBUG:-$ZV_CLAUDE_DEBUG} ]] \
    && dbg=(--debug-file "${TMPDIR:-/tmp}/bench-claude-debug.log")
  if command -v -- "$bin" >/dev/null 2>&1; then
    ( bench_ai_export && "$bin" --permission-mode auto "${dbg[@]}" "$@" )
  else
    print -r -- "  claude not on PATH"
    return 1
  fi
}

# Bench convo session. Opens Claude in the bench, then drives it via expect:
# `-n <name>`, /color <random>, and finally stages ">>name" in the input box
# WITHOUT sending it — no tokens are spent until you press Enter yourself.
# `convo` alone lists the 24 most recently active convo folders; type its
# number, or a (new or existing) name, or leave blank for a plain shell.
convo() {
  emulate -L zsh
  local name=$1 line i color
  local -a recent
  if [[ ! -d $BENCH_DIR/convos ]]; then
    print -r -- "  no bench checkout at $BENCH_DIR"
    return 1
  fi
  local other=
  [[ -z $BENCH_WINDOW && -n $BENCH_OTHER_WINDOW && -d $BENCH_OTHER_WINDOW ]] && other=1
  if [[ -z $name ]]; then
    recent=( "$BENCH_DIR"/convos/${~BENCH_CONVO_GLOB:-[a-zA-Z0-9]*}(/Nom[1,24]) )
    print -r -- ""
    for (( i = 1; i <= ${#recent[@]}; i++ )); do
      printf "  %2d  %-26s" $i "${recent[$i]:t}"
      (( i % 3 == 0 )) && print
    done
    (( ${#recent[@]} % 3 )) && print
    print -r -- ""
    if [[ -n $other ]]; then
      print -r -- "   r⏎ other repo…              0  $BENCH_OTHER_WINDOW_LABEL    s⏎ just a shell"
    else
      print -r -- "   r⏎ other repo…              s⏎ just a shell"
    fi
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
      0) if [[ -n $other ]] && command -v cursor >/dev/null 2>&1; then
              print -r -- "  opening the $BENCH_OTHER_WINDOW_LABEL…"
              (env -u BENCH_MENU_DONE -u ZV_MENU_DONE cursor -n "$BENCH_OTHER_WINDOW" >/dev/null 2>&1 &)
              return 0
            fi ;;
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

  local saved_tty; saved_tty=$(stty -g 2>/dev/null)
  local pidfile; pidfile=$(mktemp -t bench-claude-pid) || pidfile=""
  (
  bench_ai_export || exit 1
  BENCH_CONVO_NAME=$name BENCH_CONVO_COLOR=$color BENCH_PIDFILE=$pidfile \
    BENCH_CONVO_BIN=${BENCH_CLAUDE_BIN:-${ZV_CLAUDE_BIN:-claude}} expect -f =(cat <<'EXPECT_EOF'
set name  $env(BENCH_CONVO_NAME)
set color $env(BENCH_CONVO_COLOR)
set timeout 25
# Claude's TUI switches on mouse-motion (DECSET 1003/1006) and focus reporting
# (1004) the instant it starts. Until interact() takes the real terminal into
# raw mode, those reports arrive on a tty that still has echo on, so every
# mouse twitch paints ^[[<35;x;yM and ^[[I across the screen before the prompt.
# Echo off for the scripted phase; interact sets raw mode itself and expect
# restores the saved modes on exit.
catch {stty -echo}
spawn -noecho $env(BENCH_CONVO_BIN) --permission-mode auto -n $name
# The launcher reads this pid back after Claude exits (`auto_note.py --exit`).
if {[info exists env(BENCH_PIDFILE)] && $env(BENCH_PIDFILE) ne ""} {
  set fh [open $env(BENCH_PIDFILE) w]; puts $fh [exp_pid]; close $fh
}
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
# the input box.
#
# Readiness: match the "Claude Code" header (~1s) plus a short settle. Waiting
# for a second footer render (which Claude >= 2.1 never does) burned a full
# timeout; and "color set" is painted as separate words with cursor moves
# between them, so the ack regex spans the escapes. 6s fallback keeps the
# worst case under 8s.
expect {
  -timeout 6 "trust this folder" {
    # Folder not trusted for this login: hand the dialog to the user, type nothing.
    interact -o -nobuffer "ZVBYE" { sleep 1.5; catch {send -- "/exit"}; sleep 0.3; catch {send -- "\r"} }
    exit
  }
  "Claude" {}
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
# Trailing space: the staged text sits in Claude's input box and whatever the
# user types lands right after it, so without the space the first word
# collides with the convo name (">>spanish-studyWhen I run…").
send -- ">>$name "
# `/e`: Claude ends its reply with the word ZVBYE, which becomes a real /exit
# (burst, then \r on its own) and the tab closes.
interact -o -nobuffer "ZVBYE" { sleep 1.5; catch {send -- "/exit"}; sleep 0.3; catch {send -- "\r"} }
EXPECT_EOF
)
  )
  local rc=$?
  # Safety net: if expect dies before interact restores the tty, the shell would
  # be left with echo off and look dead. Put the saved modes back either way.
  [[ -n $saved_tty ]] && stty "$saved_tty" 2>/dev/null
  # Same ending as a named tab: note the session, then close the window.
  bench_claude_exit "$pidfile"
  return $rc
}

# Claude Code's trust dialog, answered before the picker: a launch into an
# untrusted folder would otherwise land on that dialog mid-script (the scripted
# keys picked "No, exit"). Trust is per login (.claude.json under
# $CLAUDE_CONFIG_DIR, else ~); the bench itself is marked trusted silently.
bench_trust_check() {
  emulate -L zsh
  local cfg=${CLAUDE_CONFIG_DIR:-$HOME}/.claude.json
  local py='import json,sys
p,d,m=sys.argv[1:]
try: j=json.load(open(p))
except Exception: j={}
pr=j.setdefault("projects",{}).setdefault(d,{})
if m=="check": sys.exit(0 if pr.get("hasTrustDialogAccepted") else 1)
pr["hasTrustDialogAccepted"]=True
json.dump(j,open(p,"w"),indent=2)'
  python3 -c "$py" "$cfg" "$BENCH_DIR" check && return 0
  python3 -c "$py" "$cfg" "$BENCH_DIR" set
}

# The new-tab picker: bench convos first (`r` there opens the repo menu below).
bench() {
  BENCH_AI=claude
  if [[ -d $BENCH_DIR/convos ]]; then
    bench_trust_check
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
  # bench_menu_once auto-launches Claude from, named after the project. This
  # shell is left as a plain shell. Skipped when the window is already rooted at
  # the pick (that would just duplicate the window) and when the CLI is missing.
  if [[ $BENCH_TERM_KIND == cursor && $dir != "$BENCH_WORKSPACE_ROOT" ]] \
     && command -v cursor >/dev/null 2>&1; then
    print -r -- "  opening ${dir:t} in a new Cursor window…"
    # Unset the done-markers: belt and braces. The tty comparison in
    # bench_should_hook already survives inheritance, but the new window has
    # no business carrying this shell's marker at all.
    (env -u BENCH_MENU_DONE -u ZV_MENU_DONE cursor -n "$dir" >/dev/null 2>&1 &)
    return 0
  fi

  cd -- "$dir" || return 1

  bench_claude
}

# After Claude exits in a named tab: write that session's note now, show one
# line saying where it went, and close the tab. "/exit" (or "/e") means "done
# with this window" — nobody has to check whether the note was taken. If the
# note fails, the shell stays open with the reason.
bench_claude_exit() {
  emulate -L zsh
  local pidfile=$1 pid out rc note
  [[ -r $pidfile ]] && pid=$(<"$pidfile")
  rm -f "$pidfile"
  [[ -n $pid ]] || return 0
  note=$BENCH_HOME/core/tools/auto-note/auto_note.py
  [[ -f $note ]] || return 0
  print -P "%F{213}[auto-note] writing the session note...%f"
  out=$(python3 "$note" --exit "$pid" 2>&1)
  rc=$?
  print -r -- "${out:-[auto-note] no output}"
  if (( rc == 0 )); then
    sleep 2
    exit 0
  fi
  print -P "%F{red}[auto-note] tab left open - run /note in a new session, or close it by hand.%f"
  return 0
}

# Launch Claude in the current directory under the session name $1.
# Tab configs carry a `title`, but Claude Code takes ownership of the tab title
# the instant its TUI starts, so the name has to be set inside Claude.
# `claude -n <name>` does exactly that (prompt box, /resume picker, terminal
# title), so expect is left with only the random /color to type. No staged >>
# message here — these are project tabs, not convos. Falls back to a plain
# launch if expect is missing or no name was given.
bench_claude_named() {
  emulate -L zsh
  local name=$1 color
  if [[ -z $name ]] || ! command -v expect >/dev/null 2>&1; then
    bench_claude
    return $?
  fi

  # Random session colour, same as convo(). This is Claude Code's own session
  # colour, not the Warp tab colour — a tab config's static `color` still owns
  # the tab and nothing here overrides it.
  color=${BENCH_COLORS[$(( RANDOM % ${#BENCH_COLORS[@]} + 1 ))]}

  local saved_tty; saved_tty=$(stty -g 2>/dev/null)
  local pidfile; pidfile=$(mktemp -t bench-claude-pid) || pidfile=""
  (
  bench_ai_export || exit 1
  BENCH_RENAME_NAME=$name BENCH_RENAME_COLOR=$color BENCH_PIDFILE=$pidfile \
    BENCH_RENAME_BIN=${BENCH_CLAUDE_BIN:-${ZV_CLAUDE_BIN:-claude}} expect -f =(cat <<'EXPECT_EOF'
set name $env(BENCH_RENAME_NAME)
set color $env(BENCH_RENAME_COLOR)
set timeout 25
# Echo off for the scripted phase (mouse/focus reports would paint garbage);
# interact sets raw mode itself and expect restores the saved modes on exit.
catch {stty -echo}
spawn -noecho $env(BENCH_RENAME_BIN) --permission-mode auto -n $name
# The launcher reads this pid back after Claude exits, to know which session
# gets its note (`auto_note.py --exit`).
if {[info exists env(BENCH_PIDFILE)] && $env(BENCH_PIDFILE) ne ""} {
  set fh [open $env(BENCH_PIDFILE) w]; puts $fh [exp_pid]; close $fh
}
# Match the spawned pty to the real terminal, now and on every resize.
proc syncsize {} {
  global spawn_out
  set d [stty size]
  stty rows [lindex $d 0] columns [lindex $d 1] < $spawn_out(slave,name)
}
syncsize
trap syncsize WINCH
# Same readiness rule as convo(): header match plus a short settle, then the
# ack regex. Only /color is typed — `-n` handles the name natively. The command
# goes in as one instant burst so Claude reads it as a paste and the
# slash-command menu never opens, then \r goes separately as a real Enter (a
# \r inside the burst becomes a newline in the input box and nothing submits).
expect {
  -timeout 6 "trust this folder" {
    # Folder not trusted for this login: hand the dialog to the user, type nothing.
    interact -o -nobuffer "ZVBYE" { sleep 1.5; catch {send -- "/exit"}; sleep 0.3; catch {send -- "\r"} }
    exit
  }
  "Claude" {}
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
# `/e`: Claude writes the note itself and ends its reply with the word ZVBYE.
# Seen in the output, it becomes a real /exit; the tab then closes.
interact -o -nobuffer "ZVBYE" { sleep 1.5; catch {send -- "/exit"}; sleep 0.3; catch {send -- "\r"} }
EXPECT_EOF
)
  )
  local rc=$?
  [[ -n $saved_tty ]] && stty "$saved_tty" 2>/dev/null
  bench_claude_exit "$pidfile"
  return $rc
}

# Which terminal is this? Warp differs in exactly one respect: it registers its
# shell integration AFTER sourcing rcfiles, so the menu must wait for
# $WARP_BOOTSTRAPPED or it runs mid-handshake and kills paste and the Project
# Explorer. Cursor (and Zed) have no such handshake, so their first precmd is safe.
#
# Keyed off TERM_PROGRAM alone, as one exclusive case: ZED_TERM and similar
# markers are inherited by every child process, while TERM_PROGRAM is re-set by
# whichever terminal owns the pty.
#
# Cursor is a VS Code fork and reports TERM_PROGRAM=vscode exactly like VS Code.
# Cursor ships through ToDesktop (bundle id com.todesktop.*) and its git
# extension exports the app path into the terminal environment; plain VS Code
# matches neither and is left alone.
typeset -g BENCH_TERM_KIND=
case $TERM_PROGRAM in
  WarpTerminal) BENCH_TERM_KIND=warp ;;
  zed)          BENCH_TERM_KIND=zed  ;;
  vscode)
    [[ $__CFBundleIdentifier == com.todesktop.* \
       || $VSCODE_GIT_ASKPASS_NODE == */Cursor.app/* ]] && BENCH_TERM_KIND=cursor
    ;;
esac

# Basename of the project whose root is $PWD; non-zero if $PWD is not a
# project root. Decides auto-launch vs. menu vs. leave-it-alone.
bench_project_here() {
  local p
  for p in "${BENCH_PROJECTS[@]}"; do
    [[ $PWD == "$p" ]] && { print -r -- "${p:t}"; return 0; }
  done
  return 1
}

# True when $PWD is a parent of a project or sits inside one, without being a
# root itself. Editors open the terminal at the workspace root, and a workspace
# is often the containing folder rather than one project — a case that matches
# no root and would otherwise get silence. Kept narrow so unrelated repos stay quiet.
bench_near_project() {
  local p
  for p in "${BENCH_PROJECTS[@]}"; do
    [[ $p == "$PWD"/* || $PWD == "$p"/* ]] && return 0
  done
  return 1
}

# True when a Warp tab config already covers $PWD — this window will run
# bench_claude_named itself and the hook must stay out of the way. Compared with
# spaces normalised to hyphens, because a tab config `name` must be URI-safe
# ("thumbnail-drop" for the folder "thumbnail drop") — see core/shell/wp.
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

  # The catch-up tool (tools/on-demand/catchup, if this bench has it) queued this
  # tab: claim the oldest entry (line 1 title, line 2 ai, line 3 prompt file)
  # and launch it instead of the menu. Entries older than 2 min are leftovers
  # from a failed run: dropped.
  local q t a f
  for q in $BENCH_CATCHUP_QUEUE/*.tab(N.Om); do
    if [[ -n $(find "$q" -mmin +2) ]]; then rm -f -- "$q"; continue; fi
    mv -- "$q" "$q.taken" 2>/dev/null || continue
    { read -r t; read -r a; read -r f } < "$q.taken"; rm -f -- "$q.taken"
    cd -- "$BENCH_DIR" || return 1
    if [[ $a == codex ]]; then
      print -n -- "\e]0;${t}\a"; codex "$(<$f)"
    else
      bench_claude -n "$t" "$(<$f)"
    fi
    return $?
  done

  # In the bench (or when BENCH_DIR is missing — see the fail-safe below), show
  # the picker.
  if [[ $PWD == "$BENCH_DIR" || ! -d $BENCH_DIR ]]; then
    bench
    return $?
  fi

  # Warp reaches here only via `wp` opening a plain window at a repo with no tab
  # config — bench_should_hook has already established that. The folder name
  # is the project name; no picker, no prompt.
  if [[ $BENCH_TERM_KIND == warp ]]; then
    bench_claude_named "${PWD:t}"
    return $?
  fi

  # Cursor (and Zed) only, and only in another project's root: start Claude
  # named after that project. This stands in for Warp's coloured tab configs —
  # the editors open terminals at the workspace root, so the directory itself
  # is the trigger.
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
# Warp keeps a $PWD condition: ordinary Warp tabs open in the bench
# (settings.toml working_directory_config) while a tab config opens in its own
# project directory, so "cwd is the bench" cleanly separates the two. Tab
# configs cannot set env vars, so BENCH_NO_MENU=1 is unavailable to them. Beyond
# the bench, register only for a git toplevel under BENCH_DEV_DIR that no tab
# config covers: exactly a `wp`-opened plain window, which would otherwise sit
# as a bare shell. Tab-config windows are excluded, so Claude never launches twice.
#
# Cursor (and Zed) always register; bench_menu_once decides from $PWD. A
# Cursor folderOpen task sets BENCH_NO_MENU=1 to avoid a double launch.
#
# Fail-safe: if BENCH_DIR does not exist, the menu appears in every tab
# (annoying, visible) rather than in none (reads as "the picker broke").
#
# The done-marker holds the TTY it was set on, not a bare 1. It is exported so a
# nested shell in the SAME terminal stays quiet, but an exported 1 would also
# travel into anything that terminal launches — including `cursor -n`, whose new
# window hands that environment to its own terminals. Comparing against $TTY
# keeps the nested-shell suppression while letting a genuinely new terminal fire.
bench_should_hook() {
  [[ -o interactive && -t 0 && -z ${BENCH_NO_MENU:-$ZV_NO_MENU} \
     && $BENCH_MENU_DONE != "$TTY" && $ZV_MENU_DONE != "$TTY" ]] || return 1
  case $BENCH_TERM_KIND in
    warp)        [[ $PWD == "$BENCH_DIR" || ! -d $BENCH_DIR ]] && return 0
                 [[ $PWD == $BENCH_DEV/*/* && -d $PWD/.git ]] || return 1
                 ! bench_warp_tab_config_here ;;
    zed|cursor)  return 0 ;;
    *)           return 1 ;;
  esac
}

# Older names, kept so tab configs, folderOpen tasks and habits keep working.
() {
  local f
  for f in choose_ai ai_export claude trust_check repo_menu claude_exit \
           claude_named project_here near_project warp_tab_config_here \
           menu_once should_hook; do
    functions[zv_$f]="bench_$f \"\$@\""
  done
}

if bench_should_hook; then
  export BENCH_MENU_DONE=$TTY
  # The folder the window was opened with: an editor spawns its terminals at
  # the workspace root, so the first prompt's cwd is that root. bench_repo_menu
  # uses it to tell "pick a different repo" (new window) from "pick the one I'm
  # already in" (launch here); it must be captured before any cd moves us.
  typeset -g BENCH_WORKSPACE_ROOT=$PWD
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd bench_menu_once
fi
