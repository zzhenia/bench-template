---
name: obsidian-style
description: Apply ZV-Bench's editor preferences (font, spacing, theme) to all Obsidian vaults
---

# Obsidian Style — Single Source of Truth

Applies consistent editor preferences across all Obsidian vaults. Preferences are stored in this skill directory (appearance.json, app.json, typography.css) — the single source of truth. Vaults with their own theme (cssTheme) or different font are skipped unless `--force` is used.

## Trigger

- `/obsidian-style` — apply preferences to all vaults
- Natural language: "apply the Obsidian look", "set up vault styling", "sync editor style"

## How to use

```bash
# View what will change (dry run)
~/ZV-Bench/skills/obsidian-style/obsidian-style.py --dry-run

# Apply to all vaults
~/ZV-Bench/skills/obsidian-style/obsidian-style.py

# Force apply to vaults that have their own theme
~/ZV-Bench/skills/obsidian-style/obsidian-style.py --force
```

## After running

After the script applies preferences, **reload Obsidian** to see the changes:
- Open Obsidian
- Press `Cmd+P` (Mac) or `Ctrl+P` (Linux/Windows)
- Type "Reload app without saving"
- Press Enter

Changes take effect immediately after reload. Font, line-height, letter-spacing, and word-spacing will be applied to all vaults.

## What it sets

### appearance.json (Obsidian settings)
- `textFontFamily`: Noto Serif
- `baseFontSizeAction`: false (don't scale fonts on window size)
- `theme`: system (follow OS dark/light mode)

### app.json
- `readableLineLength`: false (no column width limit)

### typography.css (custom CSS)
- `line-height`: 1.7 (generous vertical spacing)
- `letter-spacing`: 0.015em (subtle letter spacing)
- `word-spacing`: 0.02em (subtle word spacing)

## Skip-own-theme rule

Vaults that already have a custom theme (`cssTheme` set in their settings.json) or use a different font than Noto Serif are **skipped by default**. Use `--force` to override this and apply preferences anyway.

Example: a vault with a community theme will be skipped unless you pass `--force`.

## Flags

- `--dry-run`: Show what would change without modifying vaults
- `--force`: Override skip-own-theme rule and apply to all vaults

## Preferences location

- **appearance.json**: `~/ZV-Bench/skills/obsidian-style/appearance.json`
- **app.json**: `~/ZV-Bench/skills/obsidian-style/app.json`
- **typography.css**: `~/ZV-Bench/skills/obsidian-style/typography.css`

Edit these files to change defaults for all vaults. Run the script again to propagate changes.
