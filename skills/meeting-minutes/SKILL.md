---
name: meeting-minutes
description: Turn a meeting transcript or raw notes into Confluence meeting minutes (PI or personal) in the house format — draft by default, published on approval. Load when Zhenia pastes a transcript, AI summary or notes and asks for meeting minutes, meeting notes, or a Confluence page for a meeting.
---

# Meeting minutes → Confluence

The skill version of the MeetingMinutes desktop app (`~/dev/meetings-follow-up`,
`app/formatter.py`). Same output, no app: you write the Markdown, the script
converts it and creates the page.

```sh
python3 ~/dev/dev-ZV/ZV-Bench/scripts/confluence-minutes.py pi <file.md>            # draft (default)
python3 ~/dev/dev-ZV/ZV-Bench/scripts/confluence-minutes.py pi <file.md> --publish  # live page
python3 ~/dev/dev-ZV/ZV-Bench/scripts/confluence-minutes.py personal <file.md>
```

On the box the script is at `~/ZV-Bench/scripts/confluence-minutes.py`. `pi` reads
`config/keys-pi.env`, `personal` reads `config/keys.env`; the PI bench never touches
`keys.env`. Pages land under each space's **Meeting Notes** folder (PI space 7503885,
parent 23330821; personal space 8192023, parent 1397424130). A duplicate title gets
` (2)`, ` (3)`.

## Workflow

1. Write the minutes (format below) to a scratch file. Date = the meeting date
   Zhenia gives, else today. Instance = `pi` for Pilot Institute meetings, `personal`
   otherwise. Ask only if neither is obvious.
2. Create a **draft** unless Zhenia said to publish. Reply with the edit link and the
   open points (unnamed speakers, inferred decisions). Never post a draft and a live
   page for the same meeting.
3. On approval, run again with `--publish` from the same file (edit it first if Zhenia
   asked for changes). A Confluence draft stays one version only (`status: draft`,
   `version.number: 1`); do not try to PUT edits onto it — republish.

## Format (every section required)

```
# YYYY-MM-DD Meeting notes (Topic)

**Participants:** Name1, Name2, Name3.

**Agenda:** Topic one, topic two, topic three.

**Links:**
- [Description](URL)

## Discussion Topics

- Point one in a complete sentence.

## Decisions

- Decision stated in present tense.

## Actions

- Name does something.
```

Rules (from the app's prompt, unchanged):

- Title `YYYY-MM-DD Meeting notes` or `YYYY-MM-DD Meeting notes (Topic)`. The H1 is
  the page title; it is stripped from the body and a TOC macro takes its place. No
  other H1.
- Participants: first names, comma-separated, full stop at the end. Only people who
  speak or are addressed as present. Someone merely talked about is not a participant.
  An unnamed speaker stays `Speaker N`; say so in the reply so Zhenia can fill it in.
- Agenda: the main topics in one sentence.
- Discussion Topics: complete-sentence bullets, the main body. Cluster, but keep every
  idea, number, name and fact. Optional `###` sub-headings when the meeting had clear
  blocks.
- Decisions: present tense; agreements and conclusions.
- Actions: present tense, `Name does something`. Keep the owner given in the source.
- Links: URLs mentioned; omit the section only if there are none.
- Discussion Topics, Decisions and Actions are always present; infer sensible
  decisions and actions from context when none are stated, and say in the reply
  which ones are inferred.
- US English, Chicago style, em-dashes, double quotes. No emojis, no exclamation
  points. Spell "Johann" (the script fixes "Johan").

## Transcript hygiene

- Map speaker labels to names from context before writing ("I know Jesse mentioned…"
  means the earlier speaker is Jesse). Never guess a name with no evidence.
- Whisper mis-hears product names: "Power 107" is "Part 107", "IOPA" is "AOPA" only if
  the context is the flying association. Fix the ones you are sure of, flag the rest.
- Comments-of-the-month and small talk are not discussion topics unless they carry a
  decision or a fact worth keeping.

## Editing a draft and attaching files

- Rewrite a draft from the edited file: `… pi <file.md> --update <draft-id>` (one PUT,
  version 1; the script handles it).
- Attach a file (deck PDF, etc.) with the v1 API, `?status=draft` while it is a draft:
  `curl -u "$EMAIL:$TOKEN" -H 'X-Atlassian-Token: nocheck' -F "file=@<path>"
  "<base>/rest/api/content/<id>/child/attachment?status=draft"` (source the keys file;
  never paste the token).
- Link it from **Links** with a raw storage line, which the converter passes through:
  `- <ac:link><ri:attachment ri:filename="<file>"/><ac:plain-text-link-body><![CDATA[<text>]]></ac:plain-text-link-body></ac:link>`
