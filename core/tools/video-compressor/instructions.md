# video-compressor

Compresses screen recordings with HandBrakeCLI (VideoToolbox hardware H.265).

## Watch-folder service — `compressor.py`

Runs all the time (launchd, `schedule.plist`: at login, kept alive). Any
`.mkv/.mov/.mp4` dropped in the root of the watch folder is compressed once it
has not changed for 60 s:

- compressed copy → `<watch>/output/<name>.mp4`
- original → `<watch>/originals/<name>_orig.<ext>` (moved out, so it is never redone)
- a file another program still has open stays put until it is free

Status for dashboards: `<watch>/.compressor_status.json`. Log:
`state/video-compressor/compressor.log`. `SIGUSR1` cancels the current encode.

## One-off — `compress.sh`

`bash core/tools/video-compressor/compress.sh [1|good|2|high]` compresses the
newest recording in `OBS_DIR` (default `~/Movies/OBS`) to `<name>_compr.mp4`
beside it. Without an argument it asks.

## config/bench.env

| Key | Default | Meaning |
|---|---|---|
| `VIDEO_COMPRESSOR_DIR` | `~/Movies/video_compressor` | Watch folder |

Needs `brew install handbrake` (HandBrakeCLI).
