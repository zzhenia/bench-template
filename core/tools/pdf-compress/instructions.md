# pdf-compress

Shrinks a PDF with Ghostscript.

```
core/tools/pdf-compress/compress.sh <input.pdf> [screen|ebook|printer]
```

- `screen` 72 dpi, `ebook` 150 dpi (default), `printer` 300 dpi.
- Writes `<name>_compressed.pdf` next to the input; the original is untouched.
- Needs Ghostscript (`brew install ghostscript`).
