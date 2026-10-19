# Skills

One set, one place. Claude Code on the Mac reads these through the
`.claude/skills → ../skills` symlink; every OpenClaw agent reads the same files
out of its bench clone (`~/ZV-Bench/skills/<name>/SKILL.md`). There is no other
copy anywhere — not in `~/.claude`, not in a personality repo. A personality
repo's `skills/` holds only what is about that agent (Eva's `script-craft`,
Eva's `platforms`) plus pointer files to the shared ones.

**A skill is how to do a thing.** It is read into context and followed: how to
use Slack, how to call Toggl without hitting the quota, how Zhenia's writing
sounds. It has no code, no schedule, no state.

**An action is a thing that runs.** Code, a launchd or cron entry, a state file,
a log. Actions live in `tools/on-demand/` and `tools/recurring/` and are
what agents work on and build; some will become agents themselves.

Shared code that several actions import lives in `lib/`, not here.

## Format

`skills/<name>/SKILL.md` with frontmatter:

```
---
name: <folder name>
description: <what it is and when to load it — this line is what triggers it>
---
```

Supporting files sit beside `SKILL.md` in the same folder (`writing/VOICE.md`,
`writing/CRAFT.md`). Slash commands are skills too: `/note` is `skills/note/`. `/e` (`skills/e/`) is
`/note` plus close-the-tab: it ends with the word ZVBYE, which the launcher in
`config/warp/zshrc-picker.zsh` turns into `/exit`.

## Adding one

1. Make the folder and `SKILL.md`; the description decides when it loads, so
   write the triggers into it.
2. If agents use it, add a row to the table in `convos/openclaw/specs/network.md`
   and a `check-box:` line; a personality repo gets a pointer file at most.
3. Nothing to register — Claude Code discovers it on the next turn, agents on
   the next bench pull (15 min).
