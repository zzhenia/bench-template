---
name: autopilot
description: Open, deploy to, or restart the YT Autopilot app (https://ytautopilot.formulacommons.com, served from the box).
model: haiku
---

YT Autopilot runs on the box (openclaw-1) at **https://ytautopilot.formulacommons.com**. That is
the only address to give Zhenia; never mention localhost. Full spec:
`convos/openclaw/specs/network.md`, section "YT Autopilot service".

Nothing runs on the Mac. The old Mac helper (launchd `com.zvi.yt-autopilot`, Illustrator /
Photoshop actions) is switched off; bring it back only when Zhenia asks:
`launchctl load -w ~/Library/LaunchAgents/com.zvi.yt-autopilot.plist`.

```bash
BOX='ssh -i ~/.ssh/formula-server openclaw@100.96.0.28'
```

### (no argument) — open the app

`~/dev/dev-ZV/ZV-Bench/tools/on-demand/arc-tabs/arc-tabs.sh open https://ytautopilot.formulacommons.com` (or tell
Zhenia the URL).

### deploy (after any code change)

Code changes are not live until the box has them.

1. Commit and push the changed files from the bench (`git pull --rebase` first if rejected).
2. `$BOX 'cd ~/ZV-Bench && git pull -q && systemctl --user restart yt-autopilot.service && sleep 4 && systemctl --user is-active yt-autopilot.service'`

### restart

`$BOX 'systemctl --user restart yt-autopilot.service && sleep 4 && systemctl --user is-active yt-autopilot.service'`

### stop / start

`$BOX 'systemctl --user stop|start yt-autopilot.service'`. Stopping takes the site down for Zhenia.

Report: what restarted and "live at https://ytautopilot.formulacommons.com".
