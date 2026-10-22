---
name: formula-daily
description: Formula Daily — "ghost" turns a pasted piece into a Ghost post at 07:00 ET; "pub" posts to LinkedIn at 08:15 ET. Both reply with preview/queue links.
---

# Formula Daily — paste to scheduled post

**Whose skill this is: Eva.** Two entry points, one flow:

- Zhenia pastes into #formula-scripts with the word "ghost".
- Zhenia works a draft with Eva in an engagement thread (#social-media or a digest
  DM), posts it to Reddit or LinkedIn themself, then pastes the final version back
  into that same thread with "ghost".

"ghost" is a command, not a request for a cleaned-up version in chat. It means:
build the Ghost post from this, schedule it for 07:00 ET, send the link back in
the thread it came from. Returning a polished draft in Slack and stopping is the
failure mode.

## The trigger

- **"ghost" closes one post.** Everything Zhenia pasted in that thread since the
  last "ghost" is the material.
- **The paste is the whole input.** What they pasted may differ from what they
  posted — extra sentences, a reframing, a thought that never made it public.
  The paste wins over the thread's earlier drafts and over anything you could
  look up. Never sweep, never add an item they didn't hand you, never run
  `reddit_comments.py`.
- **The post never references the conversation it came from (Zhenia, 260905).**
  No link to the Reddit or LinkedIn thread, no "someone asked on Reddit", no
  subreddit name. A Daily is its own piece of writing; the reader has not read
  that thread and does not need to. `check` fails the post if a source link or
  platform name is in the body. Other links Zhenia pasted (a plugin, a repo, an
  article) are fine and get woven into the sentence they belong to.
- **Several "ghost"s in a sitting** = several posts, on consecutive free days, in
  the order sent. One at a time, each finished through `schedule` before the next
  one starts. See Batches.
- **"ghost" with nothing pasted** is a mistake. Ask in one line, in that thread,
  what to include. Do not guess.
- Exactly "ghost". Not "done", not "publish it".
- **Where the word sits does not matter (Zhenia, 260908).** "ghost" standing on
  its own line or as the first word of the message is the same command as "ghost"
  at the end. So is prose that says the text is for the blog ("this is for my
  blog", "draft this for the blog", "ghost post", "for Formula Daily"). Check for
  this **before** anything else you would do with pasted text — a paste with the
  trigger is never a Reddit/LinkedIn comment to polish, whatever thread it sits in.
  If you already answered with a polished draft and Zhenia says "that was a ghost
  posting", the paste you polished is the material: build the post from it, no
  re-send needed.

## One post at a time — never race yourself

One queue (`~/.ghost-daily` state and the Ghost site itself), shared by every session
that builds a Daily.

- **The session that receives the "ghost" owns that post end to end.** Never touch a
  post you did not create — the draft you edit is the one your own `finalize` just
  printed.
- `next-date` picks the first free day, so two posts built minutes apart land on
  different days. **Pin the date it prints and pass `--date <YYMMDD>` on every
  command for that post.** Without the flag the script refuses to touch a taken
  day, which is the guard working, not an error to route around.
- Before `finalize`, re-run `next-date`. If the day you pinned is no longer free,
  another session took it while you were writing: re-pin the new day and carry on.
- Never edit a `published` post. `scheduled` is still safe — it has not sent.

## Tooling

- Scripts: `~/ZV-Bench/tools/on-demand/ghost-blog/scripts/`
  (`daily_draft.py`, `ghost_admin.py`)
- Env: `GHOST_API_URL`, `GHOST_ADMIN_API_KEY`, `GHOST_DAILY_BANNER_URL` come from
  `~/.openclaw/keys.env` and are already in your shell. Never ask Zhenia for them.
  If `echo $GHOST_API_URL` is empty, that is an infrastructure fault: file it with
  Olga (`~/.openclaw/medic/inbox/<you>-<ts>.md`) and say in the thread that the
  post is blocked.

## Flow — on "ghost"

0. **Pin the day.**
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py next-date
   ```
   Prints the first free day, its issue number and slug. Every later command for
   this post takes `--date <that YYMMDD>` before the subcommand.

1. **Save the paste, then add the item.**
   ```bash
   printf '%s' "<Zhenia's full paste>" > /tmp/fd-paste.txt
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> add \
     --source reddit|linkedin|other --title "<working headline>" \
     --text "<1-3 sentence summary of Zhenia's take>" [--url "<pasted link>"] \
     --paste-file /tmp/fd-paste.txt [--image]
   ```
   `--paste-file` is mandatory: `check` measures the post against it. `--image`
   only when Zhenia said an image is coming.

2. **Finalize** — creates the Ghost draft, fills the issue number into subject and
   excerpt, picks the template, prints `edit_url` and `preview_url`.
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> finalize
   ```
   The output names the `template` and `template_shape`. The script chose it; you
   do not. Keep both URLs — they go to Zhenia at the end.

3. **Commission Writer for the body (Zhenia, 260914 — never write it yourself).**
   The post is Zhenia's paste shaped into the template, not a summary of it. Every
   point and every pasted link stays. `sessions_send` to `agent:writer:job-fd-<D>`
   with: the full paste, the template shape (`list`/`prose`/`image`, below), every
   link that must survive, the pinned sign-off (Writer never touches it, it goes
   on as the last paragraph verbatim), and the rule that nothing gets compressed,
   cut, or added — Writer fixes grammar, punctuation, awkward phrasing and rhythm,
   it does not rewrite the argument. Review what comes back against these shapes
   before you use it:
   - `list` — 3–4 sentence preamble, bulleted list (one point per bullet), 1–4
     sentence conclusion. No headings.
   - `prose` — plain paragraphs, paragraph for paragraph with the paste.
   - `image` — prose plus one paragraph reading exactly `[@image.png]`. Suggest an
     image prompt in your Slack message and remind them the placeholder is waiting.

   **When Zhenia attaches the image in Slack** (any template — "add the diagram I
   attached", "put it on a white background"), you place it yourself; never say the
   attachment is out of reach (260910, ZHEN-6737). Two commands, in this order:
   ```bash
   ~/.openclaw/tools/slack-file <you> <file-id> --pad 20          # → /tmp/slack-files/<id>-<name>.png
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> \
     image /tmp/slack-files/<id>-<name>.png --alt "<what the picture shows>"
   ```
   The file id (`F…`) is in the message's `files` (the thread fetch shows it). `--pad 20`
   is "white background, 20px border on all sides"; drop it if they did not ask. `image`
   uploads to Ghost, replaces `[@image.png]` if the body has it, otherwise goes after the
   first paragraph (`--after N` for elsewhere), backs the old body up, and refuses to add
   a picture the post already carries — it compares the images themselves, so a rename or
   Ghost's own re-encoding does not sneak a second copy in. Run `check` afterwards as usual.

   Links are woven into the sentence they belong to, anchored on the phrase they
   are about — never a bare URL, never a standalone link line, and never a link
   back to the source thread. Never open the body
   with a heading that repeats the title. Voice: `~/ZV-Bench/skills/writing/VOICE.md`,
   first person as Zhenia, field notes rather than a news roundup. **The Daily
   keeps its sign-off and takes no closing question** — the open-question rule is
   for social drafts only.

3b. **Fact-check before `check` runs (Zhenia, 260914).** Every named author,
   book, study or statistic in the paste or in Writer's draft gets verified with
   a real `web_search` before you move on — this is what would have caught the
   260914 mix-up (Cal Newport's context-switching argument is *Deep Work*, not
   *Slow Productivity*). Fix a wrong attribution at the source, keeping the
   paste's point intact; if a claim can't be verified at all, say so in the
   thread instead of shipping it or guessing.

4. **Title.** No issue number in the title, ever. Replace the whole title with
   your headline (or Zhenia's own first line if it reads as one), then:
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> sync-title
   ```
   `finalize` ends the body with a two-line sign-off drawn from a pool of 150.
   The script draws it, pins it to this post's state file and never redraws it,
   and no sign-off repeats until all 150 have been used. Keep the one you find,
   exactly as written, as the last paragraph. Never pick one yourself, never
   reword it, never carry one over from another post. No feature image on dailies.

5. **Tag it from the closed vocabulary** in `~/ZV-Bench/tools/on-demand/ghost-blog/tags.json`.
   Never invent a tag.
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py tags
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> tag Obsidian PKM
   ```
   1–3 topics, most relevant first. `check` fails without one.

6. **`check` is the gate.**
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> check
   ```
   Fix every problem it prints and run it again until `"ok": true`. Never argue
   with it, never work around it, never schedule from the Ghost UI.

7. **Schedule** — re-runs `check` and refuses if anything is off. Sets 07:00
   America/New_York on the post's date, publish + email, all members. There is no
   approval wait, and you never end a session with the Daily still a draft.
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/ghost-blog/scripts/daily_draft.py --date <D> schedule
   ```

8. **Reply in the same thread** — the thread the "ghost" arrived in, never a new
   message or another channel. The message carries, always:
   - **`preview_url`** — the rendered post, readable without publishing it
   - **`edit_url`** — the Ghost editor, for Zhenia's own edits
   - the slug, the template used, and the send time (07:00 ET, with the date)
   - for `image`, the prompt suggestion and the placeholder reminder

   Both links come straight out of `finalize`, `check` and `schedule`. A message
   with only one of them, or with neither, is incomplete — Zhenia should never
   have to go looking for the post.

8c. **`--date <D>` is not optional** on `body set`, `tag` or `sync-title`: without it
   the command targets whatever post today's date resolves to, which on 260906
   overwrote the post publishing that morning with another day's body. Those three
   now refuse a post that is already `scheduled` or `published` unless `--date` names
   it. Every `body set` also prints `previous_body` — the file holding the body it
   replaced, under `~/.ghost-daily/body-backups/`. That file, not Ghost's revision
   history, is how a wrong write gets undone: `body set --date <D> --file <that path>`.

9. **Revisions land verbatim.** Apply exactly what Zhenia says, re-run `check`,
   confirm the post is still `scheduled`. If they ask you to shorten it, run
   `daily_draft.py --date <D> trim-ok` first — it waives the body-length rule for
   that post only. Never run `trim-ok` on your own judgement.

## Post grounding — never edit the wrong post

The 260823 incident: asked to edit "the draft", the agent opened yesterday's
already-published post and edited that.

- Pin the slug and post id the moment `finalize` prints them, and name the slug in
  every Slack message about that post.
- Check status before any edit. `published` → stop, and ask Zhenia first, naming
  the slug. `scheduled` is safe; it has not sent.
- A reply in your thread is about the post you just named, not some other file or
  package. If it genuinely doesn't fit, quote what you think they mean and ask one
  yes/no.
- One draft per day. `add` is idempotent per link (or per title when there is no
  link) — re-sending an item updates it rather than duplicating it.

## Batches

Each "ghost" is its own post: own date, own template, own tags, own state file.
Work strictly one at a time in the order sent, and never start post B before post
A is `scheduled` — `next-date` only advances once a day is taken. One Slack reply
per post so Zhenia can see which post landed on which day.

## Silence is the failure

If `check` still fails after two fix rounds, or a script call errors, or you don't
know what the paste means, say so in the thread immediately — plainly, naming the
slug and what is blocking you. Never retry quietly, never leave Zhenia waiting.
Script and Ghost API faults also go to Olga's inbox; what Zhenia gets is the one
line about their post.

## pub — Ghost post + Scripts doc

When Zhenia says "pub" (instead of just "ghost"), the flow is: build the Ghost post
at 07:00 ET **and** append the post to Formula Daily — Scripts so the nightly queue
job picks it up. No approval step.

The LinkedIn post follows the rules at https://zvi.atlassian.net/wiki/spaces/~288856893/pages/1474428929 (Formula — Everyday CTA Policy). **Eva reads that page every time; the skill does not copy or embed the policy.** The text gets the social-craft passes; the open-question rule applies (unlike the Daily).

On "pub", after `schedule` succeeds for the Ghost post:
1. Locate the LI markdown file (`writing/ZV/editorial/Formula/<YYMMDD>_LI_*.md`), commissioned
   from Writer — never write it yourself. Eva has the Reddit or LinkedIn permalink from the
   engagement thread and passes it through in Writer's brief so Writer can write the Source
   line correctly (same hand-off for the YT short in step 2 below).
   The file must contain a `Source: [blog](https://blog.formulacommons.com/formula-daily-<YYMMDD>/), [reddit](<permalink>)`
   line as the **first line of the body** (after the `## FD26-NNN · Title` heading). Use
   `[linkedin](<permalink>)` in place of `[reddit](...)` when the Daily came from a LinkedIn
   thread instead of Reddit. Blog-only (drop the bracketed second link) when the Daily has no
   public origin. If the line is missing or wrong, fix it before running `fd_scripts_append.py`.
   This is the line `strip_source_lines()` removes before Buffer and that the Scripts doc
   backfill added to existing entries.
2. Commission Writer for the YT short script for that FD ID (one short per pub):
   - Same shape as the 053–073 batch: a `Source: [blog](<link>), [reddit](<permalink>)` line
     (or `[linkedin](<permalink>)` for a LinkedIn-origin Daily, or blog-only when there is no
     public origin — same format and permalink hand-off as step 1) citing the Daily, its own
     hook (not the LI post reworded), and the lead-magnet CTA by ZVLM ID.
   - First-mention rule: every real person named in the script gets a 1–2 word descriptor on first mention — see `skills/writing/SKILL.md` Universal Rules.
   - Dense-opener rule: if the script's first sentence packs jargon or context the viewer lacks, add one short plain lead-in before it — see `skills/writing/VOICE.md` (Lead-in before a dense opener).
   - Writer saves it as `writing/ZV/editorial/Formula/<YYMMDD>_FD26-NNN_short.md`.
   - Wait for Writer to deliver before running the append.
   - If the short has not arrived by the time everything else is done, append LI only and
     tell Kitty in one line. Never skip silently.
3. Run:
   ```
   python3 tools/on-demand/ghost-blog/scripts/fd_scripts_append.py \
     --li <li_file> [--yt <yt_file>]
   ```
   The script reads the next free FD26 ID from the **tracker** (Formula Daily tab, ID
   column, sheet `1zaFnxMkVRwRSE2pF3j0IU7Y2MIzOl48jNlOMkik9vC0`) — not a running count
   — backs up the doc, and appends one entry above the grey divider of the latest LI tab
   (and latest YT tab if `--yt` was given). It is idempotent — safe to re-run if only
   `--li` was used the first time.
4. Reddit-origin Dailies only: once step 3 succeeds, save Zhenia's original comment to the
   Scripts doc (tab "<Month> <YY> RD", e.g. "October 26 RD", same FD ID):
   ```
   python3 tools/on-demand/ghost-blog/scripts/fd_reddit_archive.py \
     --fd FD26-NNN --url <comment permalink>
   ```
   Skip it for LinkedIn-origin and no-origin Dailies. The 03:30 Bogota cron archives any miss.
5. Reply in the same thread with the Ghost links only:
   ```
   Ghost (07:00 ET): [preview_url] [edit_url]
   Scripts: FD26-NNN added to [tab title]
   ```
   `[tab title]` is that RD tab name, e.g. "October 26 RD".

When Writer redrafts a LinkedIn post or Short for an existing FD ID, the brief uses that FD ID's Reddit entry in the Scripts doc as the source, not the Ghost post.

**pub NEVER schedules or drafts a post in any external tool.** `tools/recurring/fd-queue/run.py`
runs nightly and picks up ticked LI posts. Teleprompter 'Filmed' checkboxes are handled
the same way by that job.

Errors (script not found, Drive API failure, file not found): the pub section fails
silently and routes the error to Olga's inbox. The Ghost part still posts. Zhenia hears
nothing about the error, only that the Daily scheduled. If Zhenia asks why the Scripts
doc was not updated, check Olga's inbox and report the actual error in the thread.
