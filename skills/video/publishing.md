---
name: publishing
description: YouTube Shorts publishing — metadata, scheduling, and API workflow for Formula Daily and SMKS shorts
---

# YouTube Shorts Publishing

Publishing YouTube Shorts requires careful metadata configuration. This guide covers the complete API workflow for Formula Daily (FD) and SMKS (Self-Maintaining Knowledge System) shorts.

**Use the publishing API only** — never manual YouTube Studio scheduling. Videos schedule at **16:00 America/New_York time** (4 PM ET). A job short (from YT Autopilot) on a day that already has a short goes at **13:00 UTC** (9 AM ET in October); the daily Formula short keeps the evening.

---

## Publishing Workflow

1. **Source:** Editor (e.g., Videobot) renders short MP4 and uploads to Drive.
2. **Metadata assembly:** Editor fills in the SF briefs sheet; extract title, CTA, and dates from there.
3. **API publish:** Call YouTube `videos.insert()` with metadata below, then `videos.update()` to set scheduling.
4. **Confirmation:** After upload, verify metadata in YouTube Studio or via API query.

---

## Metadata: Complete Specification

### Snippet (Title, Description, Tags, Language)

**Title:** From the SF briefs sheet, "<Month YY>" tab (e.g. "October 26"), Title row, column D. Strip any `[CTA]` tag before upload.

**Description:** Three blocks separated by double newlines (`\n\n`):

1. **Hook block** (1–2 sentences): Teaser or summary of the short's topic.

2. **CTA block** (2 lines): Call-to-action text + URL. Choose one CTA from the map below based on the short's content. The text must be exact:

   | CTA Key | Text | URL |
   |---------|------|-----|
   | QUIZ | ↓ Take the quiz: how do you manage what you know? | https://tally.so/r/eqOy7e |
   | NEWSLETTER | ↓ Get the Formula Daily newsletter: | https://formulacommons.com/newsletter |
   | SMKS | ↓ Get the Self-Maintaining Knowledge System: | https://formulacommons.com/smks |
   | ZVLM-018 | Download the free Vault Memory File: | https://docs.google.com/document/d/1fawKOih_H4Ng1L96nlIEWejyiQVSIYwQPod0MgBcvlc/copy |
   | ZVLM-005 | Get the free Vibe Coding Starter Pack: | https://docs.google.com/document/d/1hOnxJFhcL5yAnnxhe0LVsdWRD459eS5I/copy |

3. **Hashtag block** (exact string, one line):
   ```
   #Shorts #PKM #KnowledgeManagement #Obsidian #NoteTaking #Zettelkasten #Productivity #SecondBrain
   ```

**Example description:**
```
In this short, we explore why capturing your first impressions is essential for knowledge retention.

↓ Take the quiz: how do you manage what you know?
https://tally.so/r/eqOy7e

#Shorts #PKM #KnowledgeManagement #Obsidian #NoteTaking #Zettelkasten #Productivity #SecondBrain
```

**Category ID:** `26` (Educational)

**Tags:** Empty array. No tags.

**Default Language:** `en-US`

**Default Audio Language:** `en-US` (US English)

### Status (Privacy, Scheduling, Kids Classification)

**Privacy Status:** `private` (use `publishAt` below to schedule; do not keep permanently private)

**Publish At:** RFC 3339 timestamp, **16:00 (4:00 PM) America/New_York time** on the scheduled publish date. Example: `2026-10-15T20:00:00Z` (4 PM ET = 20:00 UTC in October, DST).

Use `datetime` + `zoneinfo.ZoneInfo('America/New_York')` to convert:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

# During DST (UTC-4):
dt_ny = datetime(2026, 10, 15, 16, 0, tzinfo=ZoneInfo('America/New_York'))
dt_utc = dt_ny.astimezone(ZoneInfo('UTC'))
print(dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ'))  # 2026-10-15T20:00:00Z

# After DST ends (UTC-5):
dt_ny = datetime(2026, 11, 1, 16, 0, tzinfo=ZoneInfo('America/New_York'))
dt_utc = dt_ny.astimezone(ZoneInfo('UTC'))
print(dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ'))  # 2026-11-01T21:00:00Z
```

**Notify Subscribers:** notifySubscribers = False (no notification email to subscribers on publish)

**Category ID:** categoryId = 26 (Educational). Required for all Shorts.

**Made for Kids:** `False` (selfDeclaredMadeForKids: False, or madeForKids: False — both must be false)

**License:** Standard YouTube License (implicit; no custom license)

**Embeddable:** `True`

---

## Post-Upload Verification

After publishing via API:

1. Verify the video appears in YouTube Studio as private, with publish time 4 PM NY.
2. Check the description: exact hook, CTA text + URL, hashtag line.
3. Check metadata: category 26, en-US / en-US, no tags, madeForKids False, AI use No, paid promotion No.
4. At the scheduled time, YouTube will auto-publish the video (status changes to public).

If metadata does not match exactly, stop and investigate before the scheduled publish time — do not leave incorrect metadata live.

---

## API Error Handling

Common issues:

- **400 Bad Request**: CTA text or URL typo, or title contains invalid characters. Check against the spec above.
- **403 Forbidden**: YouTube quota exceeded. Check the developer console at console.cloud.google.com.
- **404 Not Found**: Video ID does not exist after upload.

When an error occurs, fix the metadata in your local config and re-call `videos.update()` with the same video ID to update the fields. Do not re-insert the video.

---

## CTA Resolution

**Title has no `[CTA]` tag:** Look up the CTA in the SF briefs sheet — check the spoken CTA line and the pop-up text for that short. Example: FD26-051 has spoken CTA "Link below" and pop-up "Get the SMKS!" → use CTA key SMKS.

**No spoken CTA at all** (the editor recorded only the lesson content): stop and ask Zhenia before publishing. Zhenia decides which CTA pairs with which short. Do not guess.
