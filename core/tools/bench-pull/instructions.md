# Bench Pull — keep this machine level with GitHub

The bench repo on GitHub is the source of truth; other machines and agents may
push to `main` during the day. This job brings their work onto the local drive
without anyone running a command. **No Claude call, no tokens** — plain bash +
git. Each bench runs its own job for itself.

## What runs, and when

`com.bench.<slug>.bench-pull` (launchd, `schedule.plist`, every **900 s** and at
load) runs `bench_pull.sh`. If the Mac is asleep, launchd fires it on the next
wake. Installed by `core/bin/install-schedules.sh`.

Each run:

1. Pre-flight: skips a tree with a rebase in progress, an `index.lock`, or a
   branch other than `main`.
2. `git fetch origin`. If `main` is not behind, it exits silently.
3. `git rebase --autostash origin/main`. `--autostash` is what makes this work
   during a live session: uncommitted edits are set aside and put back after.
4. Never commits, never pushes, never resolves a conflict.

## Settings (`config/bench.env`)

- `BENCH_GIT_SSH_KEY=~/.ssh/<key>` — fetch over ssh with this key. Unset:
  git's own credentials.

## Failure visibility

Any failure → Slack DM to the owner of `SLACK_USER_TOKEN` (`config/keys.env`),
or a macOS notification without one, saying the machine is no longer level with
GitHub and how to fix it (`git pull --rebase --autostash`), plus a session-start
notice. Throttled to one alert every **6 hours**. Success is silent.
`state/bench-pull/state.json` holds the last run; `state/bench-pull/bench-pull.log`
has the history.

## Manual

```bash
bash core/tools/bench-pull/bench_pull.sh --dry-run   # report only
bash core/tools/bench-pull/bench_pull.sh             # real run
launchctl kickstart gui/$(id -u)/com.bench.<slug>.bench-pull
```
