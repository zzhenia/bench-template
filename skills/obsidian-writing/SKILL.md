---
name: obsidian-writing
description: Drive the four-pane Obsidian writing workspace (file tree, writing pane, reference pane, Claude Code terminal) from the terminal inside the vault. Use when asked to open notes, SlipBox cards or references in Obsidian, set up the layout, tag notes to a research piece (RS-00n), or start a new draft for one.
---

# Obsidian Writing

Claude runs in the terminal pane of an Obsidian vault. The vault root is the folder with
`.obsidian/`, found by walking up from the current directory. All commands go through
`ow.sh` next to this file:

```
ow.sh layout                               four panes: files | writing | reference | Claude Code
ow.sh ref <file>...                        open in the reference pane (one tab each)
ow.sh active <file>                        open in the writing pane
ow.sh search 'tag:#RS-006'                 search tab in the reference pane (any Obsidian query)
ow.sh focus writing|reference|terminal
ow.sh tag RS-006 <file>...                 add the ID to each file's frontmatter tags
ow.sh ids                                  every "(RS-nnn)" file in the vault, by ID
ow.sh draft RS-006 <slug>                  "(RS-006) YYMMDD_<slug>.md" beside the other RS-006 files
ow.sh draft new <slug> [--folder <dir>]    next free ID, in the draft folder from the plugin settings
```

## Rules

- The reference pane is the target for everything opened on request: SlipBox notes, earlier
  pieces, skills, sources. Only the draft being written goes to the writing pane.
- Never `open obsidian://open?...` directly: it lands in whatever tab is active. Use `ow.sh`.
- Paths are vault-relative or absolute; files outside the vault cannot be opened.
- A research piece is clustered by its ID tag. Tag the notes a piece draws on with
  `ow.sh tag <ID>`; find them later with `ow.sh search 'tag:#<ID>'`.
- `draft new` takes the next number after the highest `(RS-nnn)` in the vault. Pass
  `--folder` when the piece belongs somewhere other than the default draft folder.
- If a command returns silently and nothing happens in Obsidian, the plugin is not enabled:
  Settings > Community plugins > Obsidian Writing, then "Reload app without saving".

## Setup for a new vault

`tools/on-demand/obsidian-writing/setup.sh <folder>` installs and enables the plugin
(it carries its own Claude Code terminal and builds the four panes on first load) and this
skill, then opens the folder as a vault. See that tool's `instructions.md`.
