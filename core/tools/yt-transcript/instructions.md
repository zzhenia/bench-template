# yt-transcript

Fetches a YouTube video's captions (manual or auto-generated, English) and saves
them as plain text.

```
python3 core/tools/yt-transcript/run.py <url-or-id> [--timestamps] [--output FILE]
```

- Default output: `convos/yt-transcript/<YYMMDD upload date>-<title-slug>.txt`.
- `--timestamps` prefixes each line with `[m:ss]`.
- Dependencies (`youtube-transcript-api`, `yt-dlp`, `curl_cffi`) live in a venv at
  `state/yt-transcript/venv`. The first run creates it with whatever `python3`
  runs the script; delete the folder to rebuild it.
- Use this rather than ad-hoc `yt-dlp` calls: repeated raw caption fetches get
  HTTP 429 from YouTube.
