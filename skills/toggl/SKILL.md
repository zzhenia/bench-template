---
name: toggl
description: Read or write Toggl time entries without hitting the free-plan rate limit. Use BEFORE any Toggl API call — reading entries, moving projects, retagging, editing times, backfilling, auditing hours, or writing/changing a script that talks to Toggl. Triggers on Toggl, time entries, time tracking, timesheet hours, billing hours from Toggl.
---

# Toggl

## The one rule

**The free plan meters roughly 30 API calls per hour. It does not meter rows.**

Every optimisation is the same one: *more rows per call*. A job touching 8,000
entries and a job touching 20 cost the same when batched properly. Getting
`402 Payment Required` is a signal the approach is wrong — it is almost never a
reason to wait. Budget the job in **calls** before writing any code, and if the
budget exceeds ~25, stop and find the bulk path.

Auth: `TOGGL_API_TOKEN` in `config/keys.env`. Workspace `820317`.

## Reading — one call per year, never per filter

```python
POST https://api.track.toggl.com/reports/api/v3/workspace/820317/search/time_entries
{"start_date": "2024-01-01", "end_date": "2024-12-31", "page_size": 5000}
```

`page_size` is **not** capped at 200. Pull whole years and filter **client-side**.
One request per `description`/`tag_ids`/`project_ids` variant spends the hourly
budget on reads before a single row is touched.

Rows nest entries — flatten before counting:

```python
for row in rows:
    for te in row["time_entries"]:
        eid = te["id"]                 # what you PATCH
        pid = row.get("project_id")
```

Dead ends, do not retry:

| Path | Why it fails |
|------|--------------|
| `GET /api/v9/me/time_entries` | Hard 90-day floor. Fine for recent work, silently misses all history. |
| `search/time_entries.csv` | No entry-ID column. Nothing to PATCH. |

The Reports API is the **only** route to data older than 90 days.

## Writing — 100 entries per call

```python
PATCH https://api.track.toggl.com/api/v9/workspaces/820317/time_entries/{comma,separated,ids}
[{"op": "replace", "path": "/project_id", "value": 221084475}]
```

Up to **100 IDs** per call. Returns `{"success": [...], "failure": [...]}`.

- **The payload must be a LIST.** A bare dict returns
  `400 "the payload should be an array"`. Never write a per-entry PUT fallback
  for that 400 — a silent fallback is what turned a 20-second job into a
  ten-hour crawl.
- **Tags are addressed by NAME**: `{"op":"add","path":"/tags","value":["admin"]}`
  works; `/tag_ids` returns `500 Invalid path`. `remove` keeps sibling tags.

### When each entry needs a *different* value

Bulk PATCH applies the same ops to every ID, so per-entry values (each entry a
different `start`, say) cannot share a call. Before falling back to one
`PUT /workspaces/820317/time_entries/{id}` per entry:

1. **Group by value.** Entries sharing a target project, tag or time still batch.
2. **Cut the row count.** Rewrite only rows that actually need it — audit
   client-side from a single bulk read first, never row by row.
3. **Fix it at the source.** A daily job writing a handful of rows costs nothing;
   only a one-off backfill is ever big. Correct the job so the backfill never
   needs repeating.
4. Only then spend PUTs, at ~25/hour, resuming across the wall.

## Rate limits

`402` and `429` bodies both carry the exact reset. Parse it, never guess:

```python
m = re.search(r"reset in (\d+) seconds", body_text)
wait = int(m.group(1)) + 5 if m else 300
```

Reads and writes appear to meter separately — reads often still work after a
write wall. Any script that writes in bulk must **persist progress after every
batch**, so a quota wall or a kill costs nothing and a re-run resumes.

## Before writing anything

1. Record rollback data (original values per entry) in the state file first.
2. Print the matched rows grouped by rule and read them. An unfiltered run once
   moved 199 entries belonging to other clients into Pilot Institute.
3. Test a destructive op on one entry, verify, restore, then go wide.
4. Verify with a fresh sweep — count workspace entries before and after.

## Environment

- `source config/keys.env` does not export. Use
  `set -a && . config/keys.env && set +a` before a heredoc Python block.
- The Mac sleeps after 1 min idle. Wrap long runs in `caffeinate -dimsu`.
- `timeout` does not exist on macOS.

## Reference

| Thing | ID |
|-------|-----|
| Workspace (ZVI personal) | 820317 |
| Project: Pilot Institute | 221084475 |
| Project: Formula | 193469887 |
| Project: work (multi-client) | 153914401 |
| Tag: admin | 11560762 |
| Tag: R&D | 20748602 |

Inside Pilot Institute, untagged means direct assigned work; `admin` and `R&D`
mark everything else. Everything in the project is billable.

Full playbook with worked call budgets and the classification regexes:
`tools/on-demand/toggl-bulk-edit.md`. Working implementations:
`tools/on-demand/toggl-pi-consolidate.py` (has `--rollback`),
`tools/recurring/pi-toggl-fill/fill_entries.py`.
