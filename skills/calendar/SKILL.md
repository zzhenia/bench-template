---
name: calendar
description: Read or manage Zhenia's Google Calendar through the existing OpenClaw helper. Use for availability, event lookup, scheduling, or Calendar access diagnosis; not for Drive or Sheets.
---

# Google Calendar

Use the existing helper at `~/ZV-Bench/scripts/gcal.sh`. The target calendar is
already shared with the service account with writer access. Do not install another
connector, request new credentials, change sharing, or use `primary` as the calendar ID.

## Ownership

Calendar is personal admin work owned by Kitty. An agent that receives an ordinary
Calendar request routes it through Kitty under the network rules. Olga may diagnose or
verify the capability, but Calendar does not become part of her medic role.

This skill grants no permission to change an agent's model, tools, rollout coverage, or
spending limits.

## Run the helper

The gateway process may not carry `ZV_GOOGLE_KEY_FILE`. Load only that one existing
reference from the private environment file for the command; never print the line, the
resolved path, or any key contents, and never source the whole file merely for Calendar.

```bash
bash -lc '
  set -a
  source <(grep -m1 "^ZV_GOOGLE_KEY_FILE=" "$HOME/.openclaw/keys.env")
  set +a
  exec bash "$HOME/ZV-Bench/scripts/gcal.sh" "$@"
' bash agenda 7
```

Replace `agenda 7` with the required helper arguments. Useful read operations:

```text
agenda [days]    upcoming events without descriptions
get <eventId>    one event in full
cals             calendars visible to the service account
```

For a metadata-only access check that does not list events:

```text
raw GET /calendars/{cal}/events?maxResults=1&fields=accessRole
```

Do not report that Calendar is absent or disconnected until that check has failed twice.
Then follow the network skill's normal capability-gap route to Olga.

## Writes

Create or change an event only from an explicit request. Establish the exact title,
date including year, start and end, timezone, destination calendar, and whether a URL is
the meeting location before writing. Prefer explicit RFC3339 times with offsets; do not
use `quick` when any detail could be interpreted two ways.

Before creating, inspect the destination time range for a matching event. Make one write,
then retrieve the returned event ID and verify title, times, timezone, and calendar. If the
write result is missing or uncertain, reconcile by searching the same range before any
retry; uncertainty is not permission to create a duplicate. Never delete an event without
an explicit request.
