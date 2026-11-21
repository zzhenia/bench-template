# Python repin

Keeps bench jobs on a Homebrew Python that has their libraries.

- **Runs:** whenever Homebrew changes `/opt/homebrew/bin` (launchd `com.bench.<slug>.python-repin`, WatchPaths), plus daily at 10:17. Runs on `/usr/bin/python3`, so Homebrew can't break it.
- **Does:** when `python3` moves to a newer version, it relinks half-linked Homebrew packages, installs the pinned version's packages into the new one, and checks every job's imports. If all pass, it repins `~/Library/LaunchAgents/*.plist` (reloaded), repo plists under `actions/`, `tools/` and `core/tools/`, and `~/.hammerspoon/init.lua` (reloaded, if present). If something breaks, it stays on the old version. Between upgrades it pins any job still calling the bare `python3`.
- **Tells you:** a Slack DM to the owner of `SLACK_USER_TOKEN` (`config/keys.env`) on every switch or block, otherwise a macOS notification. App wrappers in `wrappers_dir` that run the bare `python3` are only checked, never rebuilt; a breakage there is reported once. A script with an `_ensure_python()` guard restarts itself on the newest `python3.NN` that has its libraries, so it is reported only when no installed version does (`wrapper_fallback` in the state file).
- **One per Mac:** LaunchAgents are machine-wide, so one instance covers every bench. `core/bin/install-schedules.sh` skips the install when another bench already runs it; list the other benches' paths in the running bench's `config/python-repin.json` (`other_benches`) so their repo plists and modules are covered too. Separate repos checked out inside a bench are skipped.
- **Settings:** `config/python-repin.json` (`other_benches`, `wrappers_dir`, default `~/Applications/Bench Jobs`). **State:** `state/python-repin/state.json` (`pinned`, `previous`, `blocked`). Log: `/tmp/com.bench.<slug>.python-repin.log`.
- **Turn off:** `launchctl unload ~/Library/LaunchAgents/com.bench.<slug>.python-repin.plist`.
