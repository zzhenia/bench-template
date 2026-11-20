---
name: pdf-compress
description: Compress a PDF to a smaller file with Ghostscript (screen, ebook or printer quality). Use when asked to shrink, compress or reduce the size of a PDF, e.g. to fit an upload or e-mail limit.
---

If `personal/overlays/pdf-compress.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Run `core/tools/pdf-compress/compress.sh <input.pdf> [screen|ebook|printer]` (default `ebook`). It prints `before → after` and the output path (`<name>_compressed.pdf` beside the input). If the result is still too big, try `screen`; never overwrite the original.
