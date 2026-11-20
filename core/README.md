# core

The part of the bench every bench shares: skills and bench machinery. It is
published to the bench template, and benches take it with `/update`.

- `skills/` — skills any bench can use. Linked into `.claude/skills` by
  `bin/link-skills.sh`, next to the bench's own skills in `personal/skills/`.
- `bench-update/` — the daily update check and `/update`.
- `bin/` — `link-skills.sh`, `scan-personal.sh` (blocks publishing when core
  holds a personal detail), `notices.sh` (shows notices from unattended jobs at
  session start).

Rules for anything in `core/`:

- No personal details: no names, e-mail addresses, home paths, Slack or Jira
  IDs, hosts or domains. A bench's own values live in `config/`.
- A skill that needs bench-specific steps says so through an overlay: it reads
  `personal/overlays/<skill>.md` first, and the overlay wins.
- Edit core only in the bench that publishes it. Elsewhere it is overwritten by
  the next update.
