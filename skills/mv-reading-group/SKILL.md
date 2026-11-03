---
name: mv-reading-group
description: MV reading group emails (poll, nudge, confirm, summary, reminder) — where drafts live and who sends them. Read before touching a group email or tools/recurring/mv-reading-group.
---

# MV reading group — group emails

The worker (`tools/recurring/mv-reading-group/worker.py`, notes in `instructions.md`) writes every group email; Zhenia sends it.

1. **Drafts live in Gmail Drafts of zzhenia@gmail.com.** The worker saves each one through the Gmail API (gmail.modify token in `$GMAIL_TOKEN_FILE`; From Zhenia, To the participants) and stores the Gmail draft id and message id in the draft JSON (`gmail`). The Slack thread gets one line: "Draft <subject> is in Gmail Drafts." — never the full body. Nothing is saved to inbox@zheniavasiliev.com Drafts.
2. **Zhenia edits and sends from Gmail.** The worker notices a send (draft gone from Gmail Drafts, message present in Gmail Sent) and runs the follow-up: state advance, and for the confirm draft the calendar event + invites. Gone from both = deleted: held, one line in the thread.
3. **The Gmail draft is the source of truth.** Before any edit, read it back (`worker.py show <id>`), never rewrite from the stored JSON. Edit with `worker.py edit-draft <id>` (reads the Gmail draft, then updates it in place). To link a draft that already exists in Gmail: `worker.py adopt <id> <gmail-draft-id>` — never create a second copy.
4. **✅ in Slack and `worker.py approve <id>` are a fallback only.** Kitty runs `approve` only after Zhenia's explicit yes.
5. **Test with a draft addressed only to zzhenia@gmail.com** (a scratch `MVRG_WORKDIR` and `MVRG_SLACK_DRY=1`), then delete the test drafts. Never send to the group while testing. The cron runs the working-tree `worker.py`: test edits on a copy, not in place.
6. **Gmail drafts, not inbox@.** Group emails are drafts in zzhenia@gmail.com. The inbox@ Drafts folder holds none; inbox@ is only the SMTP sender and its Sent folder.
