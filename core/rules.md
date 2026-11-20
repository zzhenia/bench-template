# Core rules

Rules every bench session follows. A bench loads them with the line
`@core/rules.md` in its `CLAUDE.md`.

## Messages that need no reply

- A message that only corrects the user's previous message (a typo fix, often a
  single word ending in `*`) gets no second answer. If the correction changes
  what was asked, answer only the part that changed.
- A message that needs no response (an FYI, "let me ask X", a statement of what
  the user will do next) gets none. Do any work it implies without a reply.
