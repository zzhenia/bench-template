---
name: bench-recall
description: The bench is the team's memory — search convos/ masters, then indexes, then notes before answering about past work; how a file written to the bench gets pushed.
---

# The bench is the team's memory — look there before you answer

**Whose skill this is: every agent on openclaw-1.** One copy, here
(`~/ZV-Bench/skills/bench-recall/SKILL.md`).

Zhenia talks to all of us and to Claude on the bench. Every one of those conversations
leaves a note in `~/ZV-Bench/convos/<topic>/YYMMDD-<slug>.md`, and a nightly job folds the
notes into `_memory-master.md` (the standing summary: what it is, current state, decisions,
open questions) and `_memory-index.md` (one line per note). Ninety-odd topics, forty with a
master. That is the second brain. Nobody remembers a decision from three weeks ago; the bench
does.

## The rule

Before you answer anything that touches past work — "what did we decide about X", "where is
Y", "why is Z like that", a job or product you have not seen this session, any name you do
not recognise — run:

```sh
git -C ~/ZV-Bench pull -q --rebase --autostash 2>/dev/null   # the Mac may have pushed since your last pull
~/ZV-Bench/scripts/bench-recall.sh <two or three words>       # e.g. thumbnail drop   /   luma ffmpeg   /   casita bills
~/ZV-Bench/scripts/bench-recall.sh -c <topic> <words>          # one topic only, e.g. -c formula lead magnet
```

It searches the memory masters first, then the indexes, then the raw notes, then everything
else on the bench, and stops at the first layer with hits; each hit is `path:line` plus the
line. Open the note around a hit with `sed -n 'N,+40p' <file>`. Read the master of a topic
whole (`cat ~/ZV-Bench/convos/<topic>/_memory-master.md`, a page) when Zhenia starts on a
topic you do not know.

Pilot Institute convos (`pi`, `pi-website`, `pilot-institute`) no longer live in ZV-Bench; they
are in the separate `pi-bench` repo (`~/pi-bench` on the box, `~/dev/pi-bench` on the Mac).
`bench-recall.sh` searches both benches' `convos/` in one run, and `-c pilot-institute` finds the
folder in whichever bench has it. Hits from pi-bench print with the full path, so read a master
there with `cat ~/pi-bench/convos/<topic>/_memory-master.md`.

## How to use what you find

- Say where it came from, once, in plain words: "the 260905 note on the SMKS landing page
  says…" — a date and a topic, not a path, unless Zhenia asks for the file.
- Notes are snapshots. A note says what was true on its date; if it matters, say the date and
  check the live thing (the sheet, the ticket, the box) before acting on it.
- **A working tree is not a commit.** `git pull` above does not mean the bench is clean —
  another agent may be mid-edit in the same checkout, so a file can show content that no
  commit ever had. Before you call work *landed*, *already on the bench*, or *done*, name the
  commit and prove it: `git show <commit>:<path>` for the content, `git log -S"<string>" --
  <path>` for whether it was ever committed, `git status --short` for what is still only in
  the tree. If the file has it and `git show` does not, it is uncommitted work-in-progress —
  say that, never "done". Reading a tree as a commit nearly had a PM wave off a whole half of
  a ticket (ZHEN-6769).
- Nothing matches → say "nothing on the bench about that" and answer from what you know. Do
  not pretend to remember.
- What you learn in a session that the team should keep goes back the same way: a session
  note via `oc-note.sh` (network.md §4), never into `_memory-*.md` by hand.
- The bench is read-only for you except through the scripts named in the skills (`oc-note.sh`,
  `jira.sh`, `slipbox-write.py`, …). Never edit a note that is not yours.

## Writing a file to the bench (when Zhenia asks for one)

The bench is a git repo shared with Zhenia's Mac. **A file you write on openclaw-1 and do not
push does not exist for Zhenia** — they open the folder on the Mac and find nothing, however
clearly you named the path in Slack.

So when Zhenia asks you to put something on the bench (a draft, a brief, a folder), the write
is not finished until it is pushed, in the same turn:

```sh
cd ~/ZV-Bench
git pull -q --rebase --autostash
git add <the file(s) you wrote>
git commit -q -m "<agent>: <what it is and who asked for it>"
git push -q origin main
```

- Push only what you were asked to create. `git commit -a` sweeps up other people's work in
  progress — never use it here.
- **Editorial and long-form drafts go in `writing/ZV/editorial/<Publication>/`** — that is where
  Zhenia looks. Never invent a new top-level folder for writing; `writing/` already has one.
- Then tell Zhenia the path, and only then. "It's in `~/ZV-Bench/writing/ZV/editorial/Formula/`"
  is a claim that it is on their machine too.
- This is the one exception to "the bench is read-only for you": a direct request from Zhenia
  for a file at a path. Notes still go through `oc-note.sh`.
- If the push is rejected, say so — do not leave the file sitting unpushed and report success.

## Reading a file Zhenia says is on the bench

The same gap runs the other way, and it is the one that makes Zhenia repeat themselves.
**Zhenia pushes from their Mac; the box only pulls every 15 minutes.** So the moment they
say "the edit is ready" is precisely the moment your copy is most likely to be stale, and
`ls`-ing the path you remember gets you a confident, wrong "it isn't on the bench yet".
Zhenia has already told us once (260909) that a file they can push and we cannot see is
not acceptable — that applies to us reading as much as to us writing.

```sh
~/.openclaw/tools/bench-file <name-or-fragment>    # pulls first, then finds it
```

- Use it for **any** file Zhenia names on the bench, not just Medium drafts. It searches
  the whole repo, so a folder that moved or a partial name still resolves; newest match first.
- **Never answer "it's not on the bench" without having run it.** If it finds nothing, say
  what you searched for. If it warns that the pull failed, say that instead — "not there"
  and "I could not check" are different answers, and only one of them is Zhenia's problem.
