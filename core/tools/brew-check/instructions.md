# Homebrew check

Tests every Homebrew tool the benches use after each Homebrew change, and repairs what broke.

- **Runs:** whenever Homebrew changes `/opt/homebrew/bin` (launchd `com.bench.<slug>.brew-check`, WatchPaths), plus daily at 10:27. Waits for `brew` to finish first. Runs on `/usr/bin/python3`, so Homebrew can't break it.
- **Checks:** every Homebrew command called from bench code (`actions/`, `tools/`, `core/`, `scripts/`, `lib/`, `config/`, `.claude/`), LaunchAgents and Hammerspoon (found by scanning, so new ones are picked up). It runs real work for ffmpeg, ffprobe and HandBrakeCLI (1 s test encodes) and for gs, pdftotext and pdftoppm (renders a test PDF). Everything else gets a version check. Python and its packages are python-repin's job.
- **Repairs**, testing again after each step: install if the tool is gone → `brew link` → install missing dependencies → `brew reinstall` → reinstall the dependency whose library is missing. Repairs run with auto-update off, so they never upgrade anything else.
- **Tells you:** a Slack DM to the owner of `SLACK_USER_TOKEN` (`config/keys.env`), only when a tool is still broken after every repair (macOS notification if Slack fails). Once per broken version. Successful repairs go to the state file (`repairs`) and the log only.
- **One instance per Mac:** `core/bin/install-schedules.sh` installs it for the first bench and skips it on the others. Each other bench on the Mac goes into `other_benches` in the running bench's `config/brew-check.json`: `{"other_benches": ["~/path/to/other-bench"]}`.
- **State:** `state/brew-check/state.json` (`tools`: command → package, users, last OK; `alerted`; `repairs`). Log: `/tmp/com.bench.<slug>.brew-check.log`.
