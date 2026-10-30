---
name: shorts
description: End-to-end process for YouTube Shorts — FD (Formula Daily) and SMKS product shorts. Follow this with no other context.
---

# YouTube Shorts — Edit Process

Read `skills/video/SKILL.md` first (one line: renders run on the Mac, never on the box).

---

## Inputs

- **Raw footage** — provided per batch; file order 1 < 2 < 3 = chronological takes.
- **FD briefs sheet** (`1jJVdseF6OFLrZkMn7D3WvdxvF11TWkTiIbWvjsnVnPg`) — source for
  FD26-0NN ids and SF Type per short.
- **Scripts doc, teleprompter tab** — ground truth for correcting ASR captions.

---

## Take selection

- **Always use the last take.** When multiple takes exist, the take number is spoken at
  the start ("Number N, …"). File order determines which is last: file 1 < 2 < 3.
- Trim the spoken take announcement from the output — it never appears on screen.
- Flag any repeated lines visible mid-short for Zhenia's review before publishing.
- Formula shorts end on the closing line Zhenia shot with the cold opens ("Full breakdown's linked."), after the short has paid off.

---

## Cutting

- Remove pauses and retakes.
- The spoken "Number N, …" announcement at the start of a take is cut from the footage,
  not just hidden in captions, so QR and duration calculations remain accurate.
- **Cut directly from the original footage at 1080 × 1920, lanczos scaling, libx264 crf 12.**
  Never cut from a compressed intermediate or archive copy (see `skills/video/SKILL.md`
  Picture quality rule — the 261008 double-encode incident).

---

## Render profile

Values sourced from `~/.openclaw/workspace/videobot/media/render_short.py` (approved
2026-09-09). Verify every value against `tools/on-demand/fd-shorts/render_fd.py` when it
lands on origin/main; report any mismatch to Kitty before rendering.

### Frame
- Output: **1080 × 1920** (9:16), **30 fps**
- Codec: **libx264**, preset **medium**, crf **16**, pixel format **yuv420p**, scaling **lanczos**
- Audio: **aac**, 192 kbps

### Title card
- Duration: **5 seconds**
- Background band: mint **#6CFFB1**, full width, height auto-fit to text
- Title text: **up to 3 lines**, Archivo Bold, title case, black **#000C28**
- Greedy wrap: a word stays on its line whenever it fits within 960 px; never push a
  word down to balance line lengths. Font size is the largest (220 down to 36) whose
  wrap fits in 3 lines
- Line height: render_fd's pitch **× 1.1025** (1.05 × 1.05)
- The text block sits in the vertical middle of the band: the gap above the first line's
  cap tops equals the gap below the last line's descenders. Measure ink with PIL
  (`getbbox(anchor="ls")`) and place lines with drawtext `y_align=baseline`; never pad
  with font ascent/descent, which leaves the text sitting high.

### Talking head placement
- **Split screen / head in the top half:** the head (hat top to chin), not the Vision
  face box, is centred vertically in the top half. Vision's face rectangle sits about a
  quarter of its height below the head centre, so centre the window on `cy − 0.25·h`.
  Face never taller than 75% of the block.
- **Never split while the title card is up.** The title band covers the top half, so the
  head disappears. Hold the full-frame head until the title ends (5 s), or remove the
  title before switching to a split screen.
- **Screen share with preview (SF-04):** the screenshot fills the frame; the head sits in
  a small rounded square in the top-right corner, the whole head in view (hat top to
  chin, a bit of shoulders), face centred, filling most of the square. Cut it from the
  centred head track, not from the main cut. Position so it never covers text in the
  screenshot or animation; covering a box corner or window chrome is fine.
- **Screen share without preview:** when the feedback says "full screenshot", the
  screenshot fills the frame and there is no head square.
- **Animation:** the animation occupies the full 1080 × 1920 frame on its own brand
  background. Never scale it down over a blurred or stretched background.

### Captions
- Style: **boxed white** — BorderStyle 3 (opaque box), box padding (Outline field) = 14
- Font: Archivo Bold, size **76**, margin-v **340**
- **Word-by-word karaoke:** at any frame exactly one word is mint (**#6CFFB1**); all other
  words are plain white. Implementation: one Dialogue event per word, proportional-duration
  split, inline `\1c` colour override on the active word only. Do NOT use `\k` sweep — it
  lights up the whole phrase instead of one word.

### Voice EQ chain
```
highpass=f=90,
equalizer=f=3500:width_type=h:width=2000:g=3,
acompressor=threshold=-20dB:ratio=2.5:attack=5:release=60,
volume=1.2
```

### Music bed
See "### Music bed and mix" below: ducked bed, -14 LUFS, -1.5 dBTP.

---

## Audio, QA and retention (ZHEN-7361, 2026-10-21)

### Music bed and mix
- The bed ducks **5 dB** under the voice and comes back up in pauses (0.043 open, 0.024 under
  voice); `render_fd.py` prints the dip it measured on the cut.
- The mix is normalised to **-14 LUFS** with a **-1.5 dBTP** ceiling.
- Playback speed stays 1.3x for the next batch; Zhenia checks retention after it.

### QA step after render
After every `render_fd.py` run, before upload:
`python3 tools/on-demand/fd-shorts/qa.py <short.mp4> --plan plan.json --fd <id>`.
1. The script must exit 0: 1080x1920 at 30 fps, audio present, audio and video within 1 frame,
   -15..-13 LUFS, true peak <= -1.0 dBFS, no black gap (blackdetect d=0.03 pix_th=0.08).
2. Open `opening.jpg`, the `sheet_NN.jpg` contact sheets and every `join_NN_*.jpg`. Look for a
   frozen frame, a black frame, a word clipped at a join. Fix and re-render; never hand off on
   the script alone. Tick the last line of the `_qa.txt` report.

### Retention rules
- Put the hook in the first 3 s of every short.
- Make the opening readable with sound off (title band and caption carry it).
- Answer the hook's question by the end of the short.
- Keep the speaker on screen for at least half of the short.
- Keep full-screen B-roll no longer than about 3.5 s.
- Change the shot every few seconds.

## SF Types templates (October 2026)

Active templates: **Pop up, Split screen, Overlay, Animation**. Numbered left to right
in the reference JPEG: SF-01 Pop-up, SF-02 Animation, SF-03 Title, SF-04 Screen Share
(head square top right), SF-05 Overlay, SF-06 Full Screen, SF-07/08 Split Screen,
SF-09/10 Screen Share (head top, screenshot bottom).

Reference JPEG:
`My Drive / 2026/ZV/~ brand assets/Adobe templates/261008_261008 SF Types.jpg`

---

## Formula Daily shorts — FD26-0NN rules

Apply these rules to every FD short using pop-ups, split screen, or captions.

### Pop-ups

1. **Title case:** "All pop-ups use title case."
2. **Width and wrapping:** "Pop-up text is very small, and it gets cut off on the right and left because it's all fit in one line. You need to make it 90% of the width so that it wraps across multiple lines and the text is not smaller than the font size you use for the subtitles."
   - Pop-up box width: **90% of frame width = 972 px** at 1080
   - Text wraps to as many lines as needed
   - Font size: **≥ 76** (caption size)
   - Never shrink text to fit one line

### Split screen captions

When using split-screen animations, captions sit **centred on the split line (y = 960)**, never overlapping the animation panel. "When you add animations in split screen, make sure they don't overlap with the actual animation. Maybe they hang somewhere in between where the screen is split."

### Caption text accuracy

Captions must equal script/teleprompter text, corrected against the actual clip for ad-libs and omissions. "Transcribe what the actual clip says, compare it to the written notes, and then add things that are missing. Do not rely completely on transcription, because it may get some other bits wrong that are currently correct." Script text never gets replaced by transcript text.

---

## Output naming and Drive folders

- **Filename:** `YYMMDD_<id>_Luma.mp4` — date is the **render date** (always today, never
  the footage date); `<id>` is the FD26-0NN short id.
- **Same-day re-render (every short type):** a new version rendered on a day that already has
  one gets `_02`, `_03`… before the extension (`261022_0093_SF1_ai_02.mp4`). Never overwrite
  or reuse the earlier file's name.
- **Drive — footage:** `1. Filming/<YYMM>FD/`
- **Drive — edited output:** `2. Editing/<YYMM>FD/`
- **Drive — animation assets:** `1. Briefs/animations/<id>-A0n/`

Exact naming confirmed by `tools/on-demand/fd-shorts/render_fd.py` when it lands.

---

## Animation packages

Each animation package contains: brief + MP4 + HTML per ID. Animations come back from Claude Design as MP4 video + HTML.

**Split-screen animations:** delivered as the bottom 1080×960 panel only (opaque navy dotted background); never full height.
**Sketches:** stay full height (1080×1920).

Whether to use full-screen or split-screen treatment is **Zhenia's call per animation**;
do not decide unilaterally.

---

## Tool

`tools/on-demand/fd-shorts/render_fd.py` renders October FD shorts.
Not on origin/main as of 2026-10-08 (bench session landing it today). Do not run it until
it is on origin/main and Kitty approves.

**This render profile is the source of truth.** `tools/on-demand/fd-shorts/render_fd.py`
and `cut.py` must match every value here exactly (crf, preset, pixel format, scaling).
If they differ, report the mismatch to Kitty before running anything — do not silently
use the tool's values.

---

## SMKS shorts

SMKS product shorts (SF01–SF30 and future batches) follow the same render profile above.
SMKS-specific rules are below; the general take/cutting/render sections above also apply.

### QR codes and CTA IDs

Two lead magnets, each with its own CTA ID:

| ID | QR/link | CTA text |
|---|---|---|
| ZVLM-018 Vault Memory File | `https://docs.google.com/document/d/1fawKOih_H4Ng1L96nlIEWejyiQVSIYwQPod0MgBcvlc/copy` | "Download the free Vault Memory File:" |
| ZVLM-005 Vibe Coding Starter Pack | `https://docs.google.com/document/d/1hOnxJFhcL5yAnnxhe0LVsdWRD459eS5I/copy` | "Get the free Vibe Coding Starter Pack:" |

- Each short picks **one** ZVLM ID — never both, never a paired ID.
- Per-short QR overrides are defined in `render_short.py` (`SHORT_QR_OVERRIDE`); SF03,
  SF09, SF12, SF19, SF22, SF24, SF29 get the Vault QR; the remaining FREE-tagged shorts
  keep the Vibe Coding QR.

### Description format

1. Short hook line derived from the short's topic
2. Lead magnet link matching the QR code in that specific short (see table above)

### Drive folders (SMKS)

- **Editing:** `My Drive/2026/ZV/products/SMKS/2. Video/2. Editing`
- **Publishing:** `My Drive/2026/ZV/products/SMKS/2. Video/3. Publishing`
- Replace files in-place (same link, same filename). No duplicates.

### SMKS output filename

`YYMMDD_zvpd-006_SF{NN}_Luma.mp4` — render date, zero-padded number.

### Edit checklist (before marking done)

1. [ ] Word-by-word karaoke confirmed (spot-check 2+ lines frame-by-frame)
2. [ ] Correct QR code verified against SHORT_QR_OVERRIDE map
3. [ ] Spoken take announcement trimmed from start
4. [ ] Subtitle text fixes applied (from edit brief / script doc)
5. [ ] Pop-ups use title case and 90% width with wrapping (font ≥ 76)
6. [ ] Split-screen captions centered on split line (y = 960), not overlapping animation
7. [ ] Caption text matches script/teleprompter, corrected against actual clip (not vice versa)
8. [ ] All shorts uploaded to Drive, replaced in-place, no errors

### Publishing

See `skills/video/publishing.md` for complete metadata and scheduling workflow. Shorts publish via API at 4 PM America/New_York time. For FD shorts, title and CTA come from the SF briefs sheet.

### YouTube upload and publishing

SMKS shorts also use the publishing API workflow. See `skills/video/publishing.md`. Metadata is applied via Videobot's render and publish automation.

Route upload task to Videobot (`agent:videobot:main`).
