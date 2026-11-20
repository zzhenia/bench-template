---
name: video-compressor
description: Compress screen recordings and other videos with HandBrake hardware H.265 — the always-on watch folder, or a one-off run on the newest OBS recording. Use when asked to compress, shrink or re-encode a video, or when the watch-folder compressor seems stuck.
---

If `personal/overlays/video-compressor.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Read `core/tools/video-compressor/instructions.md`.

- To compress a file: move it into the watch folder (`VIDEO_COMPRESSOR_DIR`) and tell the user where the output will land. Never re-encode an original in place.
- Stuck or silent: check the service is loaded (`launchctl list | grep -i compressor`) and read the tail of `state/video-compressor/compressor.log` before changing anything.
