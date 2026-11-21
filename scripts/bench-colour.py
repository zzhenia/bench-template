#!/usr/bin/env python3
"""Give this bench's Cursor window its colour, in a dark and a light variant.

    python3 scripts/bench-colour.py <colour>     red blue green yellow purple orange pink cyan

Writes the colour to config/bench.env (BENCH_COLOR) and merges per-theme
`workbench.colorCustomizations` into .vscode/settings.json, so the window
follows the system: deep bars on a dark theme, a bright title bar over
tinted surfaces on a light one. Other keys in settings.json are kept.
Re-run with another colour to switch.
"""

import colorsys
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# colour: dark bar, dark terminal, light title bar, light title text, tint hue
PALETTE = {
    "red":    ("#4D0B14", "#380A10", "#E5484D", "#FFFFFF", 355),
    "blue":   ("#0B1F4D", "#0A1838", "#2398FF", "#FFFFFF", 214),
    "green":  ("#0B3D24", "#082C1A", "#2EA043", "#FFFFFF", 140),
    "yellow": ("#4A3B05", "#352A04", "#F5C518", "#1F1A00", 48),
    "purple": ("#2E0B4D", "#210838", "#8B5CF6", "#FFFFFF", 265),
    "orange": ("#4D2207", "#381805", "#F7801E", "#2A1300", 26),
    "pink":   ("#4D0B33", "#380825", "#E8559E", "#FFFFFF", 330),
    "cyan":   ("#063D45", "#052C33", "#22C3DD", "#032A30", 188),
}
DARK_THEMES = ["Default Dark+", "Default Dark Modern", "Dark+", "Dark Modern",
               "Cursor Dark", "Cursor Dark High Contrast", "Cursor Dark Midnight"]
LIGHT_THEMES = ["Default Light+", "Default Light Modern", "Light+", "Light Modern",
                "Cursor Light"]


def tint(hue: int, lightness: float) -> str:
    r, g, b = colorsys.hls_to_rgb(hue / 360, lightness, 0.75)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def blocks(colour: str) -> tuple[dict, dict]:
    bar, term, title, title_fg, hue = PALETTE[colour]
    dark = {
        "titleBar.activeBackground": bar, "titleBar.inactiveBackground": bar + "CC",
        "titleBar.activeForeground": "#FFFFFF",
        "activityBar.background": bar,
        "statusBar.background": bar, "statusBar.foreground": "#FFFFFF",
        "terminal.background": term,
    }
    light = {
        "titleBar.activeBackground": title, "titleBar.inactiveBackground": title + "CC",
        "titleBar.activeForeground": title_fg,
        "activityBar.background": tint(hue, 0.90), "activityBar.foreground": bar,
        "statusBar.background": bar, "statusBar.foreground": "#FFFFFF",
        "sideBar.background": tint(hue, 0.95), "editor.background": tint(hue, 0.975),
        "panel.background": tint(hue, 0.955),
        "terminal.background": tint(hue, 0.965), "terminal.foreground": bar,
    }
    return dark, light


def main() -> int:
    colour = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
    if colour not in PALETTE:
        print(f"usage: bench-colour.py <{'|'.join(PALETTE)}>", file=sys.stderr)
        return 2

    env = ROOT / "config" / "bench.env"
    text = env.read_text() if env.exists() else ""
    if re.search(r"^BENCH_COLOR=", text, re.M):
        text = re.sub(r"^BENCH_COLOR=.*$", f"BENCH_COLOR={colour}", text, flags=re.M)
    else:
        text += ("" if text.endswith("\n") or not text else "\n") + \
            f"\n# Window and session colour, set by setup.sh / scripts/bench-colour.py.\nBENCH_COLOR={colour}\n"
    env.write_text(text)

    path = ROOT / ".vscode" / "settings.json"
    settings = json.loads(path.read_text()) if path.exists() else {}
    dark, light = blocks(colour)
    custom = {k: v for k, v in settings.get("workbench.colorCustomizations", {}).items()
              if not (k.startswith("[") and k[1:-1] in DARK_THEMES + LIGHT_THEMES)}
    custom.update({f"[{t}]": dark for t in DARK_THEMES})
    custom.update({f"[{t}]": light for t in LIGHT_THEMES})
    settings["workbench.colorCustomizations"] = custom
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(settings, indent="\t") + "\n")
    print(f"✓ Bench colour: {colour} (dark and light variants in .vscode/settings.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
