# Homebrew check

Tests every Homebrew tool the bench uses after each Homebrew change, and repairs what broke.

- **Runs:** whenever Homebrew changes `/opt/homebrew/bin` (launchd `com.bench.brew-check`, WatchPaths), plus daily at 10:27. Waits for `brew` to finish first. Runs on `/usr/bin/python3`, so Homebrew can't break it.
- **Checks:** every Homebrew command called from bench code under `actions/`, `tools/` and `scripts/`, plus LaunchAgents and Hammerspoon (found by scanning, so new ones are picked up). It runs real work for ffmpeg, ffprobe and HandBrakeCLI (1 s test encodes) and for gs, pdftotext and pdftoppm (renders a test PDF). Everything else gets a version check. Python and its packages are python-repin's job.
- **Repairs**, testing again after each step: install if the tool is gone → `brew link` → install missing dependencies → `brew reinstall` → reinstall the dependency whose library is missing. Repairs run with auto-update off, so they never upgrade anything else.
- **Tells you:** a Slack DM (`SLACK_USER_TOKEN` in `config/keys.env`), only when a tool is still broken after every repair (macOS notification if Slack fails). Once per broken version. Successful repairs go to `state.json` (`repairs`) and the log only.
- **One instance per Mac:** `setup.sh` installs it once; other benches on the same Mac add their path to `other_benches` in `config.json`.
- **State:** `state.json`. Log: `/tmp/com.bench.brew-check.log`.
