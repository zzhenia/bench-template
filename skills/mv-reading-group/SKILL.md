---
name: mv-reading-group
description: MV reading group emails (poll, nudge, confirm, summary, reminder) — where drafts live and who sends them. Read before touching a group email or tools/recurring/mv-reading-group.
---

# MV reading group — group emails

1. **Gmail Drafts of zzhenia@gmail.com are the single source of truth.** The worker (`tools/recurring/mv-reading-group/worker.py`) writes every group email there and nowhere else. The Slack thread gets one line: "Draft <subject> is in Gmail Drafts."
2. **Only Zhenia sends.** No agent, worker or script sends a reading-group email, from any mailbox, for any reason: not on "send", "go ahead", ✅ or `approve`. `send_mail` raises; `approve` only checks whether Zhenia has sent the draft.
3. **No Slack approvals.** Nothing waits on a ✅. When Zhenia sends a draft from Gmail, the worker sees it in Gmail Sent and runs the follow-up (state advance; for the invite, the calendar event).
4. **Edits:** read the Gmail copy back first (`worker.py show <id>`), then `worker.py edit-draft <id>`. Zhenia's edits in Gmail win.
5. **Wrong draft:** replace or delete it in Gmail Drafts. Never send a correction yourself.
6. **Test** with a draft addressed only to zzhenia@gmail.com, a scratch `MVRG_WORKDIR` and `MVRG_SLACK_DRY=1`; delete the test drafts after.
