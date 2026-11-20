# Warp setup kit

The bench's terminal setup: Warp, plus the shell layer it shares with Cursor
(`core/shell/bench.zsh`). Settings here are applied by `core/env/apply.py`
(see `core/env/README.md`), on setup and on every `/update`.

## Contents

| File | What it is |
|------|------------|
| `settings.toml` | Warp settings the bench needs, merged into `~/.warp/settings.toml`. `{{BENCH_DIR}}` becomes the bench folder |
| `keybindings.yaml` | Custom keybindings, merged into `~/.warp/keybindings.yaml`. Flat `"<action>": <keys>` map, one binding per action |
| `img` | Executable — opens a Claude Code `[Image #N]` attachment from the on-disk cache. Install to `~/.local/bin/` |
| `core/shell/wp` | Executable — opens a project in a **new window** via `warp://…?new_window=true`, the only way to control the Project Explorer root. Symlink into `~/.local/bin/` |

A bench's own tab configs (one per project, with machine paths) live in its
`config/warp/`, not here.

## Apply on a new machine

1. `python3 core/env/apply.py` — merges `settings.toml` and `keybindings.yaml`
   (and the Cursor and Claude Code settings), backing each file up first.
   Warp settings sync can re-serialise the file over edits made while Warp
   runs: if a value does not stick, quit Warp (Cmd+Q) and run it again.
2. Add `source "<bench>/core/shell/bench.zsh"` to `~/.zshrc`. Projects go in
   `config/projects.tsv`, settings in `config/bench.env`. Check with
   `zsh -i -c 'type bench; type bench_claude_named'`. Also
   `ln -s <bench>/core/shell/wp ~/.local/bin/wp`.
3. Install the `img` helper onto `PATH`:
   `cp core/env/warp/img ~/.local/bin/img && chmod +x ~/.local/bin/img`.
   **`~/.local/bin` is not on `PATH` by default on a clean machine** — check
   with `which img`, and if it comes back empty add
   `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`.
4. Copy the bench's `config/warp/tab_configs/*.toml` (if any) to
   `~/.warp/tab_configs/` and edit each `directory` line.
5. Relaunch Warp. Most keys hot-reload; `default_session_mode` needs the
   relaunch.

**Permission mode is set in two places on purpose** — `--permission-mode auto`
on the CLI in `zshrc-picker.zsh`, and `permissions.defaultMode: "auto"` in
`~/.claude/settings.json`. Keep both. Claude Code has run at least one
migration that resets the auto-mode opt-in (`hasResetAutoModeOptInForDefaultOffer`
in `~/.claude.json`), after which sessions come up in `manual` until the
setting reasserts. To audit which mode sessions actually started in:

```sh
cd ~/.claude/projects/<encoded-project-path>
for f in $(ls -t *.jsonl | head -5); do
  echo "$f: $(python3 -c "
import json
print([json.loads(l)['permissionMode'] for l in open('$f') if json.loads(l).get('type')=='permission-mode'])")"
done
```

A leading run of `default` means that session opened in manual mode. This
only works for bare Claude Code CLI sessions — OpenClaw's agent runtime
writes a `mode` field instead of `permissionMode`, so the audit returns empty
arrays there. On those machines `~/.claude.json` is the authoritative source
for the auto-mode opt-in state.

Requirements: macOS, zsh, Warp, Claude Code on PATH (the picker degrades to a
plain shell without it), `expect` (ships with macOS).

## Design decisions worth not relearning

- **Tab title belongs to Claude Code**, not the shell. An OSC title set
  before launching a TUI survives milliseconds. Renaming goes through
  Claude's `/rename`, which Warp's tab inherits.
- **Warp is not scriptable (yet).** `warpctrl` (tab rename/colour CLI) is
  feature-flagged off on stable as of `v0.2026.08.05`; the Settings >
  Scripting page doesn't exist and the bundled wrapper is absent. Warp-side
  tab colour therefore stays manual — session colour uses Claude's `/color`.
- **Keystroke injection uses `expect`**, because TIOCSTI is blocked on macOS
  without root. Inside the expect script, every command is sent as one
  instant burst (reads as a paste, so Claude's slash-command menu never
  opens — typed char-by-char the menu fuzzy-matches and hijacks Enter onto a
  recent command), and `\r` is sent separately (inside a burst it becomes a
  newline in the input box and nothing submits).
- **Readiness and acks: match the header, never word-painted text.** Claude
  paints footer and ack lines word-by-word with cursor moves between them, so
  a literal like `"color set"` never matches and the wait silently runs to its
  timeout. Wait for the `Claude Code`
  header, settle 0.5s, and match acks with a regex that spans escapes
  (`-re {set.{0,40}to:}`). Timeouts are a fallback, never the path. Tested in
  Cursor; Warp pending.
- **`>>name` is staged, never sent** — no context loads and no tokens are
  spent until the user presses Enter, and the first message can be extended
  before sending.
- **The menu is a one-shot `precmd` hook gated on `$WARP_BOOTSTRAPPED`** —
  Warp sources rcfiles first and bootstraps after, so blocking reads at the
  bottom of `.zshrc` run mid-handshake and break the session.
- Permission modes in Claude Code ≥2.1.220: `manual`, `acceptEdits`, `auto`,
  `dontAsk`, `plan`, `bypassPermissions` — "auto mode on" is `auto`, one
  notch above `acceptEdits`.
- **Diagnose Warp from its binary, not memory:**
  `strings -a /Applications/Warp.app/Contents/MacOS/stable > dump.txt` gives
  exact menu labels, action IDs, setting keys and enums;
  `Contents/Resources/settings_schema.json` gives required fields. Dump to a
  file first — repeated regex over the binary is slow.

## Viewing Claude Code image attachments

Warp cannot render images inline — it implements **no** terminal graphics
protocol. Checked against the binary's strings (13 Aug 2026,
`v0.2026.08.05`): zero hits for sixel, zero for the kitty graphics protocol
(`_Gf=`), zero for iTerm2 inline images (`1337;File`). There is no setting to
turn this on, and no program running *inside* a pane can add it — the
emulator itself has to implement it. VS Code previews attachments only
because its Claude extension is a native UI drawing them.

Claude Code caches attachments to disk, numbered to match the `[Image #N]`
placeholder:

```
~/.claude/image-cache/<session-id>/<N>.png
```

The `img` script opens them. Install it to a directory on `PATH`:

```sh
cp core/env/warp/img ~/.local/bin/img && chmod +x ~/.local/bin/img
```

```sh
img              # most recently cached image
img 23           # image 23 from the most recently active session
img '[Image #23]'   # non-digits stripped, so you can paste the placeholder
img -l           # list cached sessions and their images
img -s <id> 23   # explicit session (id prefix is enough)
img -p 23        # print the path instead of opening
```

**It is an executable, not a shell function, on purpose.** A function only
exists at a shell prompt — typing `img 23` into Claude Code's input box just
sends it to Claude as a prompt. As a script on `PATH` it works from a shell
*and* from inside Claude Code's TUI via `!img 23`.

**Image numbers restart per session.** The `[Image #23]` you can see in one
Claude window is very often not in the newest-by-mtime session, so `img 23`
checks the newest session first and then falls back to searching every cached
session. One match wins outright; several print a disambiguation list and ask
for `-s`. Passing `-s` yourself disables the search — an explicit session is
taken as meant. Claude prunes this cache on its own.

If inline preview genuinely matters, the terminal has to change — kitty,
WezTerm, Ghostty and iTerm2 all support it, at the cost of porting the picker.

## Zed

Zed runs the **same `~/.zshrc` block** — no Zed settings change is needed. The
whole port is one dispatch on `$TERM_PROGRAM`:

| | Warp | Zed |
|---|---|---|
| Terminal id | `TERM_PROGRAM=WarpTerminal` | `TERM_PROGRAM=zed` |
| New terminal opens in | `working_directory_config` in `settings.toml` | the worktree root, always (Zed default) |
| Wait before the menu | `$WARP_BOOTSTRAPPED` — integration loads after rcfiles | none needed; plain login shell |
| Bench terminal | project picker | project picker |
| Other project roots | coloured tab config from the **+** dropdown | auto-launch `bench_claude_named`, 2s any-key bail |
| Tab colour | tab config `color` | **not available** — Zed has no terminal tab colours |

**Match on `TERM_PROGRAM`, never on `ZED_TERM`.** Zed exports `ZED_TERM=true`
and that variable is inherited by every child process, so a Warp tab launched
from inside Zed tests true for both. Since the Zed branch auto-launches Claude
and a Warp tab config already launches it itself, an overlap means Claude
starts twice in one tab. `TERM_PROGRAM` is re-set by whichever terminal owns
the pty, so the `case` on it is exclusive by construction.

What does **not** port, and has no Zed equivalent:

- **Tab colours.** Warp's per-project colour came from the tab config's
  `color`; Zed terminal tabs are monochrome. Claude's own `/color` still runs
  in `convo()` — that colours the Claude session, not the tab.
- **`~/.warp/tab_configs/*.toml`** and `settings.toml` generally. Zed needs
  neither: it opens terminals at the worktree root already, which is what the
  `$PWD` gate keys off.

Zed does have `~/.config/zed/tasks.json`, the nearest thing to a tab config,
but it is redundant here — the directory gate already covers every terminal,
including ones opened after the first.

Everything Claude-side is terminal-agnostic and already applies: the auto
permission mode, the SessionStart colour hook, the `>>topic` title hook, and
`img`. Zed's terminal renders no inline images either, so `img` still opens
them in Preview.

## Cursor

Cursor behaves exactly like Zed — same `~/.zshrc` block, no Cursor setting to
change, terminals always open at the workspace root, so the `$PWD` gate does
all the work. Bench workspace gets the picker; the other `config/projects.tsv` roots
auto-launch `bench_claude_named` with the 2s any-key bail. No tab colours.

**A pick opens a new window, because the file tree belongs to the window.**
`cd` moves the shell, not Cursor's Explorer — pick another project from a
bench window and Claude starts in the right folder while the tree still
shows the bench. So in Cursor (only) `bench()` hands the pick to
`cursor -n <repo>`: the new window is rooted at that repo, its terminal opens
at a project root, and `bench_menu_once` there auto-launches Claude renamed to the
project. The picking shell drops to a plain shell. `BENCH_WORKSPACE_ROOT`, cap-
tured at hook time from the first prompt's cwd, suppresses this when the window
is already rooted at the pick — that would only duplicate the window.

One manual step remains: a fresh Cursor window has no terminal until `Ctrl+\``,
so the auto-launch fires on that keystroke, not on window open. A
`.vscode/tasks.json` with `runOn: folderOpen` would remove it, at the cost of a
committed file per repo plus the per-workspace "Allow Automatic Tasks" prompt.

The one wrinkle is detection. Cursor is a VS Code fork and reports
`TERM_PROGRAM=vscode`, identical to real VS Code, so `TERM_PROGRAM` alone is
not enough. The `vscode` branch confirms Cursor with either of two markers:

| Marker | Cursor | VS Code |
|---|---|---|
| `__CFBundleIdentifier` | `com.todesktop.*` (Cursor ships via ToDesktop) | `com.microsoft.VSCode` |
| `VSCODE_GIT_ASKPASS_NODE` | path under `/Applications/Cursor.app/` | path under `Visual Studio Code.app` |

Both are inheritable, unlike `TERM_PROGRAM`, but they are only read once
`TERM_PROGRAM` is already `vscode` — and that is re-set by whichever terminal
owns the pty, so a Warp tab opened from inside Cursor still resolves to `warp`.
Either marker alone is sufficient; the second is there because the first comes
from Cursor's packager and could change on a repackage, and the askpass path
disappears if the git extension is disabled.

Verified in a pty harness: `cursor`/`none`/`warp`/`zed` resolve correctly per
terminal, the menu renders and takes a keypress in the bench, and a
`bench-template` terminal launches the stub with
`--model opus --permission-mode auto` and sends `/rename bench-template`.

Screenshot paste into Claude Code is **Ctrl+V** in Cursor's terminal too —
Cmd+V is an editor-level text paste, same failure as Warp.

## Opening a project in its own window (`wp`)

Warp's Project Explorer root is **derived, never set**: it walks up from the
active pane's cwd to the nearest git toplevel. Cmd+T and the `+` dropdown make
a *tab*, which re-roots the window you're already in — so the only lever is the
directory a window is born in. `wp` pulls that lever:

- A repo with a matching tab config opens via `warp://tab_config/<name>?new_window=true`
  — keeps its colour, runs `bench_claude_named` itself.
- Anything else opens via `warp://action/new_window?path=…` as a plain window,
  and the `bench_menu_once` precmd hook starts Claude there (see below).
- `wp dev` opens `~/dev`, which is not a git repo, so the tree shows every
  project at once. Deliberately left as a plain shell — it's a browse window.

**A tab config `name` must be URI-safe.** `warp://tab_config/<name>` silently
opens nothing when the name contains a space, even percent-encoded — which is
why the config for the folder `thumbnail drop` is `name = "thumbnail-drop"`.
`wp` and `bench_warp_tab_config_here` both compare with spaces normalised to
hyphens so the config still matches its folder.

**Which windows auto-launch Claude.** `bench_should_hook`'s warp arm registers on
the bench cwd (picker, as always) *or* on a git toplevel under `~/dev` that no
tab config covers. Tab-config windows are excluded on purpose: they already run
`bench_claude_named`, and registering would launch Claude twice.

## Per-project tab colours

**Tab colour is not scriptable on stable, and this was settled by testing, not
by reading.** Two routes were checked and closed:

- `warpctrl` has `Set a tab color` / `Clear a tab color` commands in the
  binary, but the CLI is feature-flagged off (`v0.2026.08.05`).
- `appearance.tabs.directory_tab_colors` exists in the binary — *"Mapping of
  directory paths to their tab color assignments"* — but is absent from
  `settings_schema.json`, and setting a tab colour from the GUI writes
  **nothing** to `settings.toml`. Verified by picking a colour, forcing a
  settings-sync rewrite, and diffing: the file came back byte-identical with
  no colour key. That state lives server-side or in-session, so it can't be
  authored or ported.

What *does* work is the `color` field on a **tab config**, per Warp's docs:
one of `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`,
resolved against the active theme. So per-project colour means one tab config
per project, opened from the dropdown next to **+**.

The split that follows: **the bench keeps the number picker** (it is where
ordinary new tabs land), and **every other project gets a coloured tab
config**. They coexist because the picker menu is gated on
`$PWD == $BENCH_DIR` — ordinary new tabs open in the bench and get the
menu; tab configs open elsewhere and don't. Tab configs cannot set environment
variables, so the existing `BENCH_NO_MENU=1` escape hatch is unavailable to them
and the `$PWD` gate is what makes this work. `bench` still summons the menu by
hand anywhere.

**Set `BENCH_DIR` correctly or the menu will not appear.** The gate keys off
it, so a value that doesn't match the machine's actual checkout disables the
picker everywhere and reads as "the picker broke". The gate therefore also
fires when `BENCH_DIR` does not exist at all — a wrong path shows the menu
in every tab (annoying, visible, fixable) rather than in none (silent). 

Each config calls `bench_claude_named '<project>'` via the pane's `commands`.
**The tab config's `title` is not what names the tab** — Claude Code takes
ownership of the tab title the instant its TUI starts, so that title lasts
milliseconds. `bench_claude_named` launches Claude under `expect` and sends
`/rename <project>` inside it, which Warp then inherits; same mechanism as
`convo()`, minus the colour (the config's `color` covers that) and minus the
staged `>>` message. It falls back to a plain launch when `expect` is missing
or no name is passed. If a tab ever comes up with dead paste or no Project Explorer,
that command is the first thing to remove (`commands = []`) (it can break the shell handshake).

## Warp facts that keep coming up

- Tabs vs panes: tab groups have join/split context menus; **panes move only
  by dragging their header** (drop on tab bar → own tab; drop into another
  tab's pane area → joined split). No menu item exists for either.
- Windows can't be named — window title mirrors the active tab. Cycle
  windows with the macOS-level `` Cmd+` ``.
- "Save as new config" on a tab saves a **tab config**
  (`~/.warp/tab_configs/*.toml`, supports `title`/`color`/per-pane
  `directory` and `command`), opened from the dropdown next to **+**. Launch
  configs (whole windows) are a separate palette feature.
- Right-click inside a pane running a mouse-tracking TUI does nothing by
  design (`terminal.mouse_reporting_enabled`); per-session fix is Command
  Palette → Toggle mouse reporting.
