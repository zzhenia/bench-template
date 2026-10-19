---
name: slack-reply-check
description: Pre-send checklist for any agent's Slack DM reply to Zhenia — two mechanical rules before sending.
---

# Slack Reply Check — Before Sending to Zhenia

**Whose skill this is: any agent (Eva, Kitty, Olga, Skillbot, Evalbot, future agents) replying to Zhenia in a Slack DM.**

Two standing rules from `~/ZV-Bench/skills/slack/SKILL.md` section 4 (reply shape) and section 6 (when Slack breaks) apply to every reply. This skill makes them an active pre-send checklist.

## The two rules

**1. Never send raw error or machinery language directly to Zhenia** (skills/slack/SKILL.md section 6)

Error messages, stack traces, exception class names, HTTP codes, lookup failures, connection resets — these belong in a report to Olga's medic inbox first (`~/.openclaw/medic/inbox/`), *then* answer Zhenia from what you can see or ask one plain question about the content. Zhenia never hears "I can't pull the thread", "let me try another way", or that a tool is down.

**2. Short answer first, 1–3 sentences** (skills/slack/SKILL.md section 4)

Lead with the direct answer or decision in 1–3 sentences (or one line). No front-loaded full explanation, drafts, reasoning, or fix write-ups unless Zhenia explicitly asks for detail. If more is warranted, wait for them to ask in a follow-up, then give it all.

## Before sending

**Procedure:**
1. Draft your reply to Zhenia in a Slack DM
2. Run the mechanical check:
   ```bash
   echo "<your draft text>" | bash ~/ZV-Bench/evals/ZHEN-6945.sh -
   ```
   Or, if your draft is in a file:
   ```bash
   bash ~/ZV-Bench/evals/ZHEN-6945.sh <filename>
   ```
3. **Exit 0 (PASS):** your reply is clear to send
4. **Exit 1 (RETRY):** rewrite the failing check(s) and run again until PASS

The eval checks:
- **Check 1:** No raw error/machinery language (Errno, Traceback, Exception, stack traces, "lookup failed", HTTP codes, session errors). If found, file it to Olga's medic inbox first, then rewrite your reply to Zhenia.
- **Check 2:** Short answer (≤3 sentences OR ≤3 bullet lines OR ≤60 words). If over, cut to the verdict; wait for a follow-up question.

## Do not

- Skip the check because the reply looks short to you — the eval's word/sentence count is the authority.
- Send a reply that fails Check 2 ("RETRY") and ask Zhenia to clarify later. Rewrite it before sending.
- Treat the eval as proof that an error was actually filed to Olga. Check 1 catches raw-error *language* (surface compliance), not the act of routing. That part is your judgment, always.

## References

- **Standing rules:** `~/ZV-Bench/skills/slack/SKILL.md` section 4 (reply shape) and section 6 (when Slack breaks)
- **Eval:** `~/ZV-Bench/evals/ZHEN-6945.sh` — mechanical check, exits 0/PASS or 1/RETRY
- **Olga's medic inbox:** `~/.openclaw/medic/inbox/` — file errors there before replying to Zhenia
