---
name: cutlist-edit
description: Text-file edit — a talking-head take becomes a finished vertical piece of content from a cutlist TSV, no timeline or editor. Read for any "one take, many lengths" job.
---

# Cutlist edit — the edit is a text file

Read `skills/video/SKILL.md` first (box only, picture-quality rules apply).
Source: a Claude Code run shown in https://www.youtube.com/watch?v=UF08V1XIUmw —
one 5-min phone take became a 15 s vertical ad in about 15 s of render.

**Principle: no timeline, no project file, no editor.** The cutlist is the whole edit.
Re-run the same command against the same take for the 15 s, 30 s, 60 s and landscape
versions; only the cutlist and the output size change.

## Pipeline

1. **Find the speech.** Silence detection marks where the speaker talks. Whisper word
   timing sharpens each edge. Use both: neither alone places a cut cleanly.
2. **Track the face.** Every frame, so the crop follows the speaker. Each cut gets a
   shot size: `wide`, `mid` or `close`.
3. **Place the cuts** in a cutlist TSV (e.g. `set/cuts-15.tsv`). One row per cut:
   `start	end	shot_size	label`. This file is the whole edit; one cutlist per length.
4. **Drop in app screens.** Screen inserts land at the moments the cutlist names
   (in the video: 40 of 441 frames).
5. **Cards on the wall beside the speaker.** Measure the speaker's right edge per cut
   off the rendered footage, then size each card to the real empty wall beside them.
6. **Captions one word at a time.** Follow the agreed style for captions; each word/ part of sentence held until the
   next one arrives.
7. **Check sync.** Frame count at 30 fps matches the cutlist, and audio/video offset is
   exactly 0 ms. Do not ship on any other value.

## Notes

- Step 5 measures the rendered cut, not the source frame: the crop in step 2 moves the
  speaker.
- Captions follow the Formula Daily caption-accuracy rules in `skills/video/shorts.md`
  when the job is an FD short.
