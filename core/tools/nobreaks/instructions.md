# nobreaks — unwrap hard-wrapped text

`nobreaks.sh` joins lines wrapped at a fixed column back into paragraphs. It
keeps blank lines, list items, headings, quotes, rules, fenced and indented
code. `nobreaks.sh -h` lists the options; `-p` reads the clipboard and writes
it back. Used by the `nb` skill. macOS clipboard (`pbpaste`/`pbcopy`).
