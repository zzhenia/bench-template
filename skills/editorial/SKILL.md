---
name: editorial
description: Everything Zhenia publishes as writing — the <YYMMDD>_ED<nnnn>_<INTENT>.md naming in writing/ZV/editorial/Formula/, Medium, reddit, and linkedin drafted here; Ghost and the social platforms posted by Zhenia.
---

# Editorial — one piece, every platform it goes to

**Whose skill this is: whichever agent Zhenia hands the material to.** It covers
everything Zhenia publishes as writing — Medium, Ghost, LinkedIn, Reddit — and
the one rule underneath all of it: **the piece lives in the bench, not on the
platform.** A platform holds a copy; `writing/ZV/editorial/Formula/` holds the
piece.

[[formula-daily]] is the Ghost end of this and keeps its own trigger ("ghost").
This file owns the naming, the file itself, and Medium.

## The file — naming, and where it lives

Everything publishable is a markdown file in `writing/ZV/editorial/Formula/`,
named:

```
<YYMMDD>_ED<nnnn>_<INTENT>.md      260908_ED0025_MD.md
```

- **YYMMDD** — the date the piece was *created*, not published. It never changes,
  including when the post goes out weeks later.
- **ED<nnnn>** — the piece. Editorial has its own four-digit sequence, separate
  from the video job ids in `convos/formula/organic-content/`, which is what the
  `ED` is for. **The same number across every platform**: the Medium post, the
  LinkedIn version and the Reddit version of one argument are `ED0025` three
  times, so the set is one `ls` away.
- **INTENT** — where this version goes: `MD` Medium, `GH` Ghost, `LI` LinkedIn,
  `RD` Reddit.

Take the next free number: `ls writing/ZV/editorial/Formula/ | sort -t_ -k2 |
tail -1`. Never renumber an existing piece, and never reuse a number for a
different argument.

## The trigger

- **"medium" closes one post.** Everything Zhenia pasted in that thread since the
  last "medium" is the material. Same rules as "ghost": the paste is the whole
  input, never sweep, never add an item they did not hand you.
- **"medium brief"** is an alias — same flow as "medium": write and commit the
  file, reply with the image brief, wait for the image. No special behaviour.
- **"medium" alone means draft.** "medium publish" (or "publish it to medium")
  means live and notifies their followers — only on those words, never inferred.
- **Where the word sits does not matter.** On its own line, first, last, or as
  prose that says the text is for Medium.
- **A filename is material too.** "260908_ED0025_MD — ready for medium"
  means publish that file, not the text of the thread. Resolve it with
  **`~/.openclaw/tools/bench-file <name>`** — never with `ls`, `find` or a path
  you remember. Zhenia edits on their Mac and the scheduled pull only runs every
  15 minutes, so the copy on the box is stale exactly when they have just told
  you a file is ready; `bench-file` pulls first, then searches the whole bench,
  so a moved folder or a partial name still resolves (newest match wins). Say
  which path you resolved to in your reply. **If `bench-file` finds nothing, say
  so and stop** — never fall back to an older version, and never rebuild the post
  from the thread. If it warns that it could not pull, say that too: "not on the
  bench" and "I could not check" are different answers to Zhenia.
- **"medium" with nothing pasted and no filename** is a mistake. Ask in one line,
  in that thread.
- A piece can go to both: `ghost` for the Daily, `medium` with
  `--canonical <the Ghost URL>` so Medium credits the original. Ghost first.

## Tooling

- Script: `~/ZV-Bench/tools/on-demand/editorial/scripts/medium_post.py`
- Env: `MEDIUM_INTEGRATION_TOKEN`, `MEDIUM_AUTHOR_ID` come from
  `~/.openclaw/keys.env` and are already in your shell. Never ask Zhenia for them.
  If `whoami` fails with 401/403, that is an infrastructure fault: file it with
  Olga (`~/.openclaw/medic/inbox/<you>-<ts>.md`) and say in the thread that the
  post is blocked. **Do not retry a rejected token.** Medium stopped issuing
  integration tokens in March 2023 — the one we hold cannot be replaced.

## Flow — on "medium"

1. **Get the file.** If Zhenia named one, `~/.openclaw/tools/bench-file <name>`
   and use it as-is — their edit pass is the version that ships, and
   you do not rewrite it. Otherwise write the draft to the bench yourself, as a
   markdown file in `writing/ZV/editorial/Formula/`, named as above. Open it
   with the header block:

   ```markdown
   ---
   type: medium-draft
   tags: [Artificial Intelligence, Productivity]   # 5 max, Title Case
   seo_description: …                              # 140–156 chars
   image: 260908_grokbot_featured.png              # next to this file
   image_alt: …                                    # one plain sentence
   canonical: https://…                            # the Ghost URL, if any
   ---

   **Title:** The headline
   **Subtitle:** The deck under it
   ```

   Front-matter `title:`/`subtitle:` work too; the `**Title:**` lines are what
   Eva already writes and the script reads either.

2. **Make it a Medium post.** Zhenia's edit pass is the prose — you do not
   rewrite a sentence of it. These four are format, not writing, and you fix them
   in the file every time without being asked:

   - **Tags are metadata, never prose.** A `Medium tags: …` line printed in the
     body is a bug. Move it to front matter (`tags: [Artificial Intelligence,
     Productivity]`). Five maximum, Medium drops the rest silently; Title Case,
     no `#`. (The script lifts a stray trailing tag line out for you — that is a
     safety net, not the place to leave it.)
   - **Every URL is a markdown link**, `[text](https://…)`. A bare
     `blog.formulacommons.com` renders as dead grey text. The subscribe link is
     the one that must never be unclickable.
   - **Every link to an owned domain carries UTMs.** Medium reports no outbound
     clicks, so the tagged link *is* the measurement — an untagged link to your
     own site is traffic you can never attribute. Tag every link that points at
     an owned property (the mid-article CTA, the italic end block, and the
     profile/bio footer, which is its own traffic source and gets its own
     `utm_content`). Never tag a third-party link: Goodreads, a source you cite,
     a competing blog — those are not yours to label, and tagging them corrupts
     the report with referrals that were never yours.

     ```
     [read more](https://<owned-domain>/<page>?utm_source=medium&utm_medium=referral&utm_campaign=<yyMMdd>_ED<nnnn>&utm_content=<placement>)
     ```

     - `utm_source` — the platform the link lives on: `medium`, `ghost`,
       `linkedin`, `reddit`.
     - `utm_medium` — `referral` for Medium.
     - `utm_campaign` — `<yyMMdd>_ED<nnnn>`, the piece id from the filename.
       This is what makes one post separable from the blob of all Medium
       traffic; a post slug would drift the moment the title is edited.
       **Exception: profile placements (Medium custom footer and bio) omit
       utm_campaign** — they render on every post without a piece name, so no
       campaign to attach. They carry only `utm_source`, `utm_medium`, and
       `utm_content`.
     - `utm_content` — which placement this is: `mid-article`, `end-block`,
       `footer` (Medium custom footer), or `bio`. The same piece carries two CTAs
       to the same page; without this they collapse into one number and you
       cannot tell which placement works. Profile placements use `footer` and
       `bio` to identify their fixed position (e.g.,
       `?utm_source=medium&utm_medium=referral&utm_content=footer`).

     **Profile placements: where and how.** Medium custom footer (Layout → Custom
     footer) and bio (Settings → Profile) are set once in Medium settings and
     never pasted into a post body. Medium renders them on every post, so
     `medium_post.py`'s gate never sees them — they bypass the post-body check.
     Measurement: these links resolve to Ghost Member sources (utm_source=medium),
     not GA4.

     Do not hardcode a hostname — the owned domain is whatever the piece
     already links to. The rule is destination-independent, and the destination
     question (blog.formulacommons.com vs zheniavasiliev.com, ZHEN-6769) is
     Zhenia's to settle. **If the site itself is the GA property, do not put
     UTMs on links *between pages of that same site*** — internal UTMs reset the
     session and hide the true referrer in GA.
   - **The subscribe CTA runs twice.** One short clickable sentence after the
     first third of the piece, where most readers still are — its own line, one
     sentence, in the voice of the paragraph it follows, never a banner. Then the
     full italic block at the end. Not three times, never in the opening two
     paragraphs.
   - **Write `seo_description:`** — 140–156 characters, the Google result for
     this piece. Left empty, Medium uses the first ~200 characters of the post,
     cut mid-sentence. It is not the subtitle reworded: say what the reader gets,
     in one sentence, with the words someone would search. The API cannot set it
     (Medium has no field for it), so the script prints it after the post is
     created and Zhenia pastes it into Story settings — **put that block in your
     reply**, with the settings link, or it never gets pasted.
   - **The subtitle doubles as the preview subtitle** (140 max) — the line under
     the title on Medium's homepage and in subscribers' inboxes. The API cannot
     set that either; the script prints it to paste into the publish dialog, and
     it goes in your reply with the SEO block. A post with a blank one shows the
     title alone everywhere it is recommended.
   - **Set `canonical:`** to the Ghost URL when the piece ran there first, so
     Medium credits the original.
   - **Write the featured-image brief.** Every post gets one — the style block
     from [[illustration]] verbatim, plus your own scene paragraph for this
     piece. It goes in your reply as a fenced block Zhenia can paste straight
     into an image generator, with the size (1500 × 844).
   - **If the image already exists, ship it.** An image sitting next to the
     markdown, or one Zhenia names, goes in `image:` and `image_alt:` in the
     front matter; the script uploads it and makes it the first thing in the
     story, which is what Medium reads as the featured image. Write the alt text
     yourself — one plain sentence describing what is in the picture.
   - **If Zhenia says to post without an image, skip the image wait and post
     immediately** — no brief, no hold.

3. **Check what will be sent.**
   ```bash
   python3 ~/ZV-Bench/tools/on-demand/editorial/scripts/medium_post.py \
       post <file.md> --dry-run
   ```
   This prints the title, tags, status, canonical, word count and the first and
   last lines, then checks the format faults you cannot fix later — missing tags,
   a `tags:` line left in the body, a bare URL. **Any `PROBLEM:` line means stop
   and fix the file**, then dry-run again. A wrong title here is free to fix;
   after step 4 it is not.

4. **Commit the file and push** — the bench flow in [[bench-recall]]. The draft
   Zhenia can edit is on Medium; the source of truth is the file.

5. **Reply with the featured-image brief.** Write the style block from
   [[illustration]] verbatim plus your own scene paragraph for this piece, in a
   fenced block Zhenia can paste straight into an image generator (size: 1500 × 844).
   End with the line: "Send me the image and I'll create the draft."

6. **When Zhenia sends the image in that thread:**
   - Download it: `~/.openclaw/tools/slack-file <you> <file-id>`
   - Save it beside the markdown as `<YYMMDD>_ED<nnnn>_featured.png`
   - Add `image: <filename>` and `image_alt: <one plain sentence>` to the front matter
   - Run dry-run; fix any `PROBLEM:` lines before continuing
   - Create the draft — drop `--dry-run`; add `--publish` only if Zhenia said publish
   - Commit the updated file and push
   - Reply in the thread with the Medium URL, the state ("in your drafts" / "live"),
     the SEO block the script printed (settings link + description to paste), and the
     preview subtitle. One message, no summary of the post.

## Flow — on "reddit"

**"reddit" closes one post** — everything Zhenia pasted in that thread since the
last "reddit" is the material, or a named ED file (its Medium version becomes the
source). Write the draft to `writing/ZV/editorial/Formula/`, named as
`<YYMMDD>_ED<nnnn>_RD.md`.

Open the file with:

```markdown
---
type: reddit-draft
suggested_subreddit: r/…        # which subreddit, if Zhenia named one
---

**Title:** The post title

Body text…
```

**The reddit version is not Medium reprinted.** Reddit removes copy-pasted articles as self-promotion and downranks them. Write a real contribution to a thread that wanted this argument: shorter than Medium, a genuine response to the thread's question or debate, never a link dump.

Rules:

- **Never the Medium text verbatim.** A real Reddit post in the voice of the sub.
- **Check the subreddit sidebar.** Some subs ban or require labelling AI-generated images. They set rules on self-promotion and external links. Read them before you draft.
- **Every link to an owned domain carries UTMs**, same as Medium:
  ```
  [text](https://…?utm_source=reddit&utm_medium=referral&utm_campaign=<yyMMdd>_ED<nnnn>&utm_content=<placement>)
  ```
- **Ask which subreddit in one line** if Zhenia didn't name one. Stop and wait for the answer before writing.
- **No image** — Reddit takes the post text only. If the sub bans AI images and Zhenia wants one, they post the link in a comment, not the body.

Flow:

1. Write the draft file as above.
2. Run it through [[social-craft]] — same passes as Medium.
3. Commit and push (bench flow in [[bench-recall]]).
4. Reply in the thread with the post inside a code block (title and body), ready for Zhenia to paste into Reddit by hand.

Reddit has no drafts API and the app registration fails — so Zhenia copies your text from the thread, posts it themselves, and the draft file is the source of truth on the bench.

## Flow — on "linkedin"

**"linkedin" closes one post** — everything Zhenia pasted in that thread since the
last "linkedin" is the material, or a named ED file (its Medium version becomes the
source). Write the draft to `writing/ZV/editorial/Formula/`, named as
`<YYMMDD>_ED<nnnn>_LI.md`.

Open the file with:

```markdown
---
type: linkedin-draft
---

**Post text:**

Body text…
```

**The LinkedIn version is short and native to the platform**, never the Medium
text reprinted. LinkedIn buries posts that are mostly external links. The link is
posted in the first *comment*, not the body — the post is the argument, the link
is the CTA that draws clicks.

Rules:

- **Never the Medium text verbatim.** A real LinkedIn post in your voice.
- **The link is the first comment, not the body.** Post the argument; reply to
  your own post with the CTA link (step 2, same UTM scheme as Medium).
- **Every link to an owned domain carries UTMs**:
  ```
  [text](https://…?utm_source=linkedin&utm_medium=referral&utm_campaign=<yyMMdd>_ED<nnnn>&utm_content=<placement>)
  ```
  - `utm_source` — `linkedin`
  - `utm_medium` — `referral`
  - `utm_campaign` — `<yyMMdd>_ED<nnnn>`, the piece id
  - `utm_content` — `first-comment` (the placement for first-comment links)
- **The Medium illustration can be reused** — add it to the file if one exists.

Flow:

1. Write the draft file as above.
2. Run it through [[social-craft]] — same passes as Medium and reddit.
3. Commit and push (bench flow in [[bench-recall]]).
4. Reply in the thread with three parts:
   - The post text in a code block
   - The first-comment link text in its own code block (if there is a link)
   - A direct link to open LinkedIn's composer with the post text prefilled

The composer link is **undocumented** (LinkedIn does not officially publish this
URL format). It opens LinkedIn's writer and fills in the text, then Zhenia hits
publish. If the link fails on first use, fall back to the code block — Zhenia
copies the text there instead.

### Building the composer link

Zhenia's post text must be URL-encoded (RFC 3986 percent-encoding: newlines → `%0A`,
spaces → `%20`). The agent builds this one-liner:

```bash
python3 -c 'import sys,urllib.parse as u; print("https://www.linkedin.com/feed/?shareActive=true&text="+u.quote(sys.stdin.read().rstrip("\n"), safe=""))' <<'EOF'
<post text>
EOF
```

Run it yourself and put the URL it prints in your reply.

LinkedIn has no drafts API and the Posts API accepts only published posts at creation.
Drafts live only in the browser's local cache — so Zhenia posts by hand, and the
draft file is the source of truth on the bench.

## Never

- **Never `--publish` on your own judgement.** Live is irreversible from here:
  the API cannot unpublish or delete, and it notifies followers.
- **Never re-run `post` to fix something.** You will create a second post, not
  update the first. See Fixing a post that is already on Medium.
- Never post material Zhenia sent to another agent.
- Never rewrite Zhenia's prose while fixing the format in step 2.

## Fixing a post that is already on Medium

The API cannot edit or delete. Medium's own editor can, and a **draft** costs
nothing to throw away:

- **Small fix, and Zhenia is happy to do it there** — they edit the draft on
  Medium directly. Then update the bench file to match, so the file stays the
  source of truth.
- **Format was wrong (tags in the body, dead links, no mid-CTA)** — that is a
  fresh run, not an edit. Zhenia deletes the draft at
  <https://medium.com/me/stories/drafts> (⋯ → Delete), you fix the file per step
  2, and you run `post` again. Say this in the thread rather than leaving them to
  work it out.
- **Already live** — nothing here undoes it. Zhenia edits or unpublishes it on
  Medium themself. Never a second post.

## LinkedIn and Reddit — use the commands

**Reddit** — use the "reddit" command (documented above). Zhenia provides the
thread and material; the agent writes the `_RD` file, runs [[social-craft]],
and replies with the draft for Zhenia to post by hand.

**LinkedIn** — use the "linkedin" command (documented above). Same flow: write
the `_LI` file, run [[social-craft]], and reply with the composer link.

Both platforms require native writing — never republish the Medium text verbatim.
Reddit removes copy-pasted articles as self-promotion. LinkedIn buries a post
that is mostly an external link. Same argument, different voice: LinkedIn short
with the link in the first comment, Reddit as a real contribution to a thread.

LinkedIn has no official drafts API (drafts live only in the browser's local
cache) and the Posts API accepts only published posts at creation, so Zhenia
posts by hand from the composer link (or code block as fallback).

The Medium illustration is reused on LinkedIn. Reddit takes no image, and some
subreddits ban or require labelling AI-generated ones — read the sidebar.

## Ghost posts are exported, not written twice

`scripts/ghost_export.py` pulls every Ghost post into the folder as `_GH` files
with its created date and id. Run it after a backfill, never as routine: Ghost
stays the place a Daily is written ([[formula-daily]]), and the export is how
those pieces become reusable material rather than something only Ghost holds.
