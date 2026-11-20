# Retire — set a Cursor tab aside

`/retire` (`core/skills/retire`) runs `retire.sh`, which marks this session's tab
with a unique terminal title, finds it by that (any tab name works) and moves it
into the first (left) tab group with Cursor's "Move Editor into First Group"
shortcut (ctrl+cmd+1). Nothing else changes: the auto-note watcher writes the
note and later closes the tab at the thresholds in `config/auto-note.json`
(`core/tools/auto-note/instructions.md`).

Needs Accessibility permission for Cursor, and
`terminal.integrated.commandsToSkipShell` in Cursor's settings to include
`workbench.action.moveEditorToFirstGroup`. A failure prints one line in the tab.
