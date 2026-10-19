#!/usr/bin/env python3
"""
Apply ZV-Bench obsidian-style preferences (from this skill directory) to all Obsidian vaults.
Single source of truth: preferences in this skill directory's appearance.json, app.json, and
typography.css. Vaults with their own theme or different font are skipped unless --force.

Usage:
    obsidian-style.py [--dry-run] [--force]
"""

import json
import shutil
import sys
from pathlib import Path


# PREFERENCE files are in this skill directory (single source of truth)
SKILL_DIR = Path(__file__).parent

# Obsidian vault registry on macOS
REGISTRY = Path.home() / "Library/Application Support/obsidian/obsidian.json"

# CSS snippet name
SNIPPET = "typography"

# Preference keys to sync
APPEARANCE_KEYS = ["textFontFamily", "baseFontSize", "baseFontSizeAction", "theme"]
APP_KEYS = ["readableLineLength"]


def load_json(path):
    """Load JSON file, return empty dict if not found."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def load_preferences():
    """Load PREFERENCE files from SKILL_DIR."""
    appearance = load_json(SKILL_DIR / "appearance.json")
    app = load_json(SKILL_DIR / "app.json")
    return appearance, app


def load_snippet():
    """Load CSS snippet from SKILL_DIR."""
    css_file = SKILL_DIR / "typography.css"
    if css_file.exists():
        with open(css_file) as f:
            return f.read()
    return ""


def load_vaults():
    """Load vaults from Obsidian registry."""
    try:
        with open(REGISTRY) as f:
            registry = json.load(f)
        return list(registry.get("vaults", {}).values())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def should_skip_vault(vault_path, src_appearance, force=False):
    """Determine if vault should be skipped (has own theme or different font)."""
    if force:
        return False, ""

    cfg_file = Path(vault_path) / ".obsidian" / "appearance.json"
    appearance = load_json(cfg_file)

    # Skip if vault has custom theme
    if appearance.get("cssTheme"):
        return True, "has its own theme"

    # Skip if vault has different font
    vault_font = appearance.get("textFontFamily")
    if vault_font and vault_font != src_appearance.get("textFontFamily"):
        return True, "has a different font"

    return False, ""


def apply_to_vault(vault_path, src_appearance, src_app, snippet, dry_run=False):
    """Apply preferences to a vault. Return True if changed."""
    cfg_dir = Path(vault_path) / ".obsidian"

    # Load current appearance
    appearance = load_json(cfg_dir / "appearance.json")
    appearance_before = json.dumps(appearance, sort_keys=True)

    # Update appearance preferences
    for key in APPEARANCE_KEYS:
        if key in src_appearance:
            appearance[key] = src_appearance[key]
        else:
            appearance.pop(key, None)

    # Add CSS snippet to enabledCssSnippets
    snippets = appearance.setdefault("enabledCssSnippets", [])
    if SNIPPET not in snippets:
        snippets.append(SNIPPET)

    # Load current app settings
    app = load_json(cfg_dir / "app.json")
    app_before = json.dumps(app, sort_keys=True)

    # Update app preferences
    for key in APP_KEYS:
        if key in src_app:
            app[key] = src_app[key]
        else:
            app.pop(key, None)

    # Check if snippet changed
    snippet_dst = cfg_dir / "snippets" / f"{SNIPPET}.css"
    snippet_changed = not snippet_dst.exists() or snippet_dst.read_bytes() != snippet.encode()

    # Determine if anything changed
    appearance_changed = json.dumps(appearance, sort_keys=True) != appearance_before
    app_changed = json.dumps(app, sort_keys=True) != app_before
    changed = snippet_changed or appearance_changed or app_changed

    if not changed:
        return False

    # Apply changes (unless dry-run)
    if not dry_run:
        snippet_dst.parent.mkdir(parents=True, exist_ok=True)
        snippet_dst.write_text(snippet)
        save_json(cfg_dir / "appearance.json", appearance)
        save_json(cfg_dir / "app.json", app)

    return True


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv

    # Load preferences from SKILL_DIR
    src_appearance, src_app = load_preferences()
    snippet = load_snippet()

    if not src_appearance:
        print("ERROR: No preferences found in skill directory")
        sys.exit(1)

    # Get vaults from registry
    vaults = load_vaults()
    if not vaults:
        print("ERROR: No vaults found in Obsidian registry")
        return

    # Apply to each vault
    for vault in vaults:
        vault_path = vault.get("path")
        vault_name = Path(vault_path).name if vault_path else "unknown"

        if not vault_path:
            continue

        # Skip if path doesn't exist
        if not Path(vault_path).is_dir():
            print(f"skip     {vault_name} (folder missing)")
            continue

        # Check skip rules
        should_skip, reason = should_skip_vault(vault_path, src_appearance, force=force)
        if should_skip:
            print(f"skip     {vault_name} ({reason}; --force to override)")
            continue

        # Apply to vault
        if apply_to_vault(vault_path, src_appearance, src_app, snippet, dry_run=dry_run):
            if dry_run:
                print(f"would    {vault_name}")
            else:
                print(f"styled   {vault_name}")
        else:
            print(f"ok       {vault_name}")


if __name__ == "__main__":
    main()
