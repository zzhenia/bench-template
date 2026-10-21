# Python repin

Keeps bench jobs on a Homebrew Python that has their libraries.

- **Runs:** whenever Homebrew changes `/opt/homebrew/bin` (launchd `com.bench.python-repin`, WatchPaths), plus daily at 10:17. Runs on `/usr/bin/python3`, so Homebrew can't break it. Installed by `setup.sh` (macOS only).
- **Does:** when `python3` moves to a newer version, it relinks half-linked Homebrew packages, installs the pinned version's packages into the new one, and checks every job's imports. If all pass, it repins `~/Library/LaunchAgents/*.plist` (reloaded), repo plists under `actions/` and `tools/`, and `~/.hammerspoon/init.lua` (reloaded, if present). If something breaks, it stays on the old version. Between upgrades it pins any job still calling the bare `python3`.
- **Tells you:** a Slack DM to yourself on every switch or block when `SLACK_USER_TOKEN` is in `config/keys.env`, otherwise a macOS notification. App wrappers in `wrappers_dir` that run the bare `python3` are only checked, never rebuilt; a breakage there is reported once.
- **One per Mac:** LaunchAgents are machine-wide, so one instance covers every bench. `setup.sh` skips the install when another bench already runs it; list the other benches' paths in that instance's `config.json` (`other_benches`) so their repo plists are repinned too.
- **Settings:** `config.json` (`other_benches`, `wrappers_dir`). **State:** `state.json` (`pinned`, `previous`, `blocked`). Log: `/tmp/com.bench.python-repin.log`.
- **Turn off:** `launchctl unload ~/Library/LaunchAgents/com.bench.python-repin.plist`.
