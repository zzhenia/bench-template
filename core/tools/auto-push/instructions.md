# Auto-Push — nightly git safety net

Commits everything finished in the bench's working tree, rebases onto
`origin/main`, and pushes, so finished work never sits unpushed because nobody
remembered `/push`. **No Claude call, no tokens** — plain bash + git. Each bench
runs its own job for itself.

## What runs, and when

`com.bench.<slug>.auto-push` (launchd, `schedule.plist`, **21:00 daily**) runs
`auto_push.sh`. If the Mac is asleep at 21:00, launchd fires it on the next
wake; if the Mac is shut down, that night is skipped. Installed by
`core/bin/install-schedules.sh`.

Each run:

0. Optional home-folder tidy (`AUTO_PUSH_TIDY_DOTFILES=yes`): keeps the newest
   **3** numbered backups of each dotfile in `~` (`~/.zshrc_old01`…) and deletes
   older ones. Deletions go to the log.
1. Pre-flight: refuses to touch a tree with a rebase/merge in progress, an
   `index.lock`, or a branch other than `main`.
2. Refreshes `AUTOMATIONS.md` with automation-status's `inventory.py` when the
   bench has it.
3. `git add -A`, then un-stages three kinds of file (same guards as `/push`):
   anything modified in the last **15 min** (a session may be mid-edit), **new**
   credential-shaped paths (`*token*`, `*secret*`, `*.key`, `*.env`…), and
   **new** files over **5 MB**.
4. Commits as `auto-push: N files across M areas (date)` with the area list in
   the body.
5. `git fetch`; if behind, `git rebase --autostash origin/main`. **A conflict
   aborts the rebase** — the local commit stays intact, nothing is
   auto-resolved. Pulling during the day is `bench-pull`'s job.
6. `git push origin main`.
7. Bench update (`core/bench-update/auto.sh`), only after a good push and only
   on a bench with `BENCH_UPSTREAM_URL`: applies the template's new changes,
   commits, pushes, and merges the bench's Cursor/Warp/Claude settings. A file
   changed both here and in the template undoes the update and opens a pull
   request on the template with this bench's version; once it is merged on
   GitHub, the next night applies the result. A settings value the user set
   differently waits for `/update` in a session.

## Settings (`config/bench.env`)

- `BENCH_GIT_SSH_KEY=~/.ssh/<key>` — push over ssh with this key (launchd has
  no ssh-agent). Unset: git's own credentials (https + keychain).
- `AUTO_PUSH_TIDY_DOTFILES=yes` — turn on step 0.

## Failure visibility

Any failure → Slack DM to the owner of `SLACK_USER_TOKEN` (`config/keys.env`),
or a macOS notification without one, plus a notice shown at the next session
start (cleared by the next good run). Success is silent. The bench update
reports the same way (notice `bench-update`): a pull request to merge, settings
waiting for an answer, or an update that could not run.
`state/auto-push/state.json` holds the last run; `state/auto-push/auto-push.log`
has the history.

## Manual

```bash
bash core/tools/auto-push/auto_push.sh --dry-run   # show what would be committed
bash core/tools/auto-push/auto_push.sh             # real run
launchctl kickstart gui/$(id -u)/com.bench.<slug>.auto-push   # fire the launchd job now
```
