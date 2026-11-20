# catchup

Catch up at the start of a session (or press `c` in the new-tab picker): list the convos worked on since the last run, then open one Cursor terminal tab per pick with an AI session already briefed. Trigger: the user types `catchup` in Claude Code, Codex or another AI session on the bench.

1. Run `core/tools/catchup/catchup.py list`. Show the user the numbered list: number, convo, and the latest note's topic in a few words. Wait for their numbers.
2. For each pick, read its notes from the list, plus `_memory-master.md` lines newer than them if needed. Check live state where a note says something is pending (git status, running services, ticket status). Write one brief per pick to `<scratchpad>/catchup/<slug>.md`:

   ```
   title: Website carousel
   >>website Catch-up. Resume ABC-123 — Course carousel polish. Source: convos/website/261119-course-carousel-polish.md

   Done: <what is finished, with numbers>
   Answered already: <decisions the user made; do not ask again>
   Open: <numbered items, owner noted>
   Needs the user: <only their decisions or manual steps>

   Start by saying where things stand in one short message, then work the open items.
   ```

   - `title:` names the work, starting with the convo's name: "Website carousel", "Billing invoice rules". 2–4 words, title case. It becomes the tab title.
   - Ticket keys always carry their title.
3. Run `core/tools/catchup/catchup.py open <scratchpad>/catchup`. Each brief opens in a new Cursor terminal tab, as `bench_claude -n "<title>" "<brief>"`. The brief is sent as the first message. `CATCHUP_AI=codex` launches Codex instead. The run is then recorded as the last one, so the next `list` starts from here.
4. Report the tabs opened and any `FAILED` lines. If the user picks nothing, run `catchup.py mark` so these notes don't show next time.

- Opening tabs needs Cursor frontmost and Accessibility permission for Cursor (System Settings → Privacy & Security → Accessibility). The script refuses to type when another app is in front.
- The script only presses Ctrl+Shift+`, after bringing this bench's Cursor window forward. The new tab's shell picks up its brief from the queue folder (hook at the top of `bench_menu_once` in `core/shell/bench.zsh`; `BENCH_CATCHUP_QUEUE` in `config/bench.env`, default `~/.bench-catchup`). Entries older than 2 min are dropped.
- A queue entry whose second line is `resume` reopens a closed session instead of starting a new one: line 1 the tab title, line 3 the session id.
- Keep Cursor in front while tabs open: about 3 s per tab.
- First run, or no `state/catchup/state.json`: the list covers the last 24 h.
