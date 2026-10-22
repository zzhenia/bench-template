---
name: video
description: Video editing trunk — which branch to read for each format (shorts, long form, social channels). Read this first, then open the branch for your format.
---

# Video Editing — Trunk

Every video task starts here. Pick the branch for your format, then follow it end to end.

## Branches

| Format | File | Status |
|---|---|---|
| YouTube Shorts — FD and SMKS | `skills/video/shorts.md` | Active |
| Shorts publishing (API metadata & scheduling) | `skills/video/publishing.md` | Active |
| Cutlist edit — one take to a finished vertical ad, any length, from a TSV | `skills/video/cutlist-edit.md` | Active |
| Long form YouTube | `tools/on-demand/lf-edit/instructions.md`, `tools/on-demand/lf-edit/style.md` | Active |
| Instagram Reels | — | Not yet written |
| Other social channels | — | Not yet written |

`style.md` (LF house style: LFnn templates = artboards of YT_video_assets.ai, layering rules, cuts) is read before any LF edit and grows with every round of review comments.

## Where tools run

**Always the box (openclaw-1), never the Mac.** The Mac's ffmpeg build lacks `drawtext`
and ASS subtitle support. Every render, subtitle burn, and audio chain runs on the box.

Rendering agent: Videobot (`agent:videobot:main`). Route all render and upload tasks there.

## Picture quality

**Cut from the original footage, never from compressed or archive copies.** Any
intermediate created during editing must be near-lossless (libx264 crf ≤ 14 at the
final output size) or stream-copied; never write a lossy intermediate and then re-encode
it for upload — that is the exact failure mode that produced the blocky shadows on
261008 (hevc_videotoolbox -b:v 6000k intermediate → libx264 veryfast final pass:
two lossy passes in sequence, first already lossy → blocky shadows, smeared detail).

**Never use a hardware encoder's bitrate mode** (`-b:v` on videotoolbox, nvenc, etc.)
for anything that will be re-encoded. Bitrate-mode encodes leave visible macro-blocking
that survives into the final file.

**Final encode:** libx264, crf ≤ 17, preset medium or slower, lanczos scaling.

**Before upload:** compare at least one frame from the source clip and from the rendered
output at the same timestamp; the shorts eval enforces this.

**Formula Daily shorts:** four additional rules (pop-up title case and sizing, split-screen caption placement, caption text accuracy) apply to FD26-0NN shorts. See `skills/video/shorts.md` Formula Daily section.

## Red line

No renders against real footage, no uploads, until the correct eval passes and Kitty
explicitly approves.
