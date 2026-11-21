#!/bin/bash
# Move this session's Cursor tab into the first (left) editor group: the "done,
# waiting to close" group. The auto-note watcher (core/tools/auto-note) writes
# its note when idle and closes the tab later, as for any other tab.
# The tab is found by a marker, not by name or focus: by the time Claude runs
# this, the user has usually clicked another tab, and tab names repeat, contain
# spaces, or change with /rename. The script writes a unique terminal title to
# this session's tty, finds the tab showing it, clicks it through Accessibility,
# then "Move Editor into First Group" (ctrl+cmd+1) moves it. The tab's own title
# is written back and focus returns to the tab and app that were in front. Needs
# Accessibility permission for Cursor, and
# terminal.integrated.commandsToSkipShell to include
# workbench.action.moveEditorToFirstGroup in Cursor's settings.json.

# This session's tty: walk up the process tree to the `claude` process.
tty=""; pid=$PPID
while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
  case "$(ps -o command= -p "$pid")" in claude*) tty=$(ps -o tty= -p "$pid" | tr -d ' '); break ;; esac
  pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
done
[ -n "$tty" ] && [ -w "/dev/$tty" ] || { echo "retire: no terminal found for this session; tab not moved" >&2; exit 1; }

workspace=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
marker="retire-$pid-$RANDOM"

errf=$(mktemp); scpt=$(mktemp)
cat > "$scpt" <<'EOF'
-- Tab labels of window 1 ("✳ the-bench, Editor Group 1" -> "✳ the-bench"), with
-- their elements. Electron sometimes answers with an empty tree; ask again.
on tabsOf()
  tell application "System Events" to tell process "Cursor"
    repeat 10 times
      set els to entire contents of window 1
      if (count of els) > 0 then exit repeat
      delay 0.3
    end repeat
    set labels to {}
    set tabEls to {}
    set sel to {}
    repeat with e in els
      try
        if subrole of e is "AXTabButton" then
          set AppleScript's text item delimiters to ", Editor Group"
          set end of labels to text item 1 of (description of e as text)
          set AppleScript's text item delimiters to ""
          set end of tabEls to contents of e
          set end of sel to ((value of e as integer) is 1)
        end if
      end try
    end repeat
  end tell
  return {labels, tabEls, sel}
end tabsOf

-- Claude tabs start with a status glyph that animates ("◐ ", "✳ "); compare without it.
on bare(t)
  if (length of t) > 2 and (id of character 1 of t) > 127 and character 2 of t is " " then return text 3 thru -1 of t
  return t
end bare

on bareList(L)
  set out to {}
  repeat with l in L
    set end of out to bare(contents of l)
  end repeat
  return out
end bareList

on setTitle(ttyPath, t)
  do shell script "printf '\\033]0;%s\\007' " & quoted form of t & " > " & quoted form of ttyPath
end setTitle

on run argv
  set marker to item 1 of argv
  set ws to item 2 of argv
  set ttyPath to item 3 of argv
  tell application "System Events"
    set frontApp to name of first process whose frontmost is true
  end tell

  -- Raise the window, then address it as window 1: references by name go
  -- stale because the title follows the active tab, whose glyph animates.
  tell application "Cursor" to activate
  tell application "System Events" to tell process "Cursor"
    perform action "AXRaise" of (first window whose name ends with ("— " & ws))
  end tell
  delay 0.3

  set {tabsBefore, elsBefore, selBefore} to tabsOf()
  -- The tab in front before the move, to go back to afterwards.
  set prevLabel to ""
  tell application "System Events" to tell process "Cursor"
    set AppleScript's text item delimiters to " — "
    set prevLabel to text item 1 of (name of window 1 as text)
    set AppleScript's text item delimiters to ""
  end tell

  setTitle(ttyPath, marker)
  set target to missing value
  repeat 10 times
    delay 0.3
    set {labels, tabEls, sel} to tabsOf()
    repeat with i from 1 to count of labels
      if item i of labels is marker then set target to item i of tabEls
    end repeat
    if target is not missing value then exit repeat
  end repeat
  -- This tab's own title: the label that the marker replaced.
  set ownLabel to ""
  set nowBare to bareList(labels)
  repeat with l in tabsBefore
    if bare(contents of l) is not in nowBare then set ownLabel to contents of l
  end repeat
  if target is missing value then
    if ownLabel is not "" then setTitle(ttyPath, ownLabel)
    error "no Cursor tab showed this session's marker"
  end if

  tell application "System Events" to tell process "Cursor"
    perform action "AXPress" of target
    delay 0.5
    key code 18 using {control down, command down}
    delay 0.3
  end tell
  if ownLabel is not "" then setTitle(ttyPath, ownLabel)

  -- Back to the tab that was in front, unless it was this one.
  if prevLabel is not "" and bare(prevLabel) is not bare(ownLabel) and prevLabel is not marker then
    set {labels, tabEls, sel} to tabsOf()
    repeat with i from 1 to count of labels
      if bare(item i of labels) is bare(prevLabel) and item i of sel then
        tell application "System Events" to tell process "Cursor" to perform action "AXPress" of (item i of tabEls)
        exit repeat
      end if
    end repeat
  end if
  if frontApp is not "Cursor" then tell application frontApp to activate
  return "moved"
end run
EOF
out=$(osascript "$scpt" "$marker" "$workspace" "/dev/$tty" 2>"$errf") || { err=$(cat "$errf"); rm -f "$errf" "$scpt"; echo "retire: could not move the tab: ${err##*error: }" >&2; exit 1; }
rm -f "$errf" "$scpt"
echo "$out"
