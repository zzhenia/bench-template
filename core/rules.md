# Core rules

Rules every bench session follows. A bench loads them with the line
`@core/rules.md` in its `CLAUDE.md`.

## Messages that need no reply

- A message that only corrects the user's previous message (a typo fix, often a
  single word ending in `*`) gets no second answer. If the correction changes
  what was asked, answer only the part that changed.
- A message that needs no response (an FYI, "let me ask X", a statement of what
  the user will do next) gets none. Do any work it implies without a reply.

## One home per thing

Every skill, tool, script and doc has exactly one folder. Before creating a
folder or file, search for an existing home for the same subject (`ls`, `grep`,
the bench index) and extend it instead.

- A skill lives once, in `skills/<name>/`; anywhere else that needs it
  (another bench, an agent's personality repo) gets a symlink or a one-line
  pointer, never a copy.
- A tool is either recurring or on-demand, not both: one folder in `tools/`,
  with its scheduled entry point inside that folder.
- A tool lives only on the bench whose work it serves; another bench does not
  get its own copy.
- Found a duplicate? Merge it into the older home, leave a pointer if something
  links to the old path, and say so in the session note.

## First port of call

Every bench has `master-instructions.md` at its root: what the bench is for,
where things live, where to look. Read it at the start of every session, before
searching anywhere else. `CLAUDE.md` names it on its first lines. `/update`
creates it when a bench has none.

## One layout

Every bench has the same skill layout: `core/skills/` (shared),
`personal/skills/` (this bench's own), and `skills/` holding links only.
`/update` removes an old copy left in `skills/` and moves a skill found only
there into `personal/skills/`.
