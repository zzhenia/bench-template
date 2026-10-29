---
name: illustrator-scripting
description: Safe Adobe Illustrator scripting from bench sessions — ExtendScript via osascript, .ai files, ArtLayer/placedItem edits, PI brand files. Triggers on Illustrator, ExtendScript, osascript, .ai file work. Rule 1 (never discard Zhenia's manual work), Rule 2 (apply only the requested changes), Rule 3 (PI palette as global swatches), Rule 4 (every PI file copies the BR-0027 reference setup), and Rule 5 (one five-layer stack in every .ai file, grids as guides on `ref`) are mandatory for every script that touches a .ai file.
---

# Illustrator Scripting — Safety Rules and Gotchas

## Why this exists

A session rebuilt `261009_BR-0027 CFI Program.ai` (referred to as EV-0001 CFI
Program A-Frame) from a script and lost Zhenia's unsaved manual edits. The
script had no concept of "is there manual work on this document right now" —
it just rebuilt the file. The two rules below exist to make that preflight
check a mechanical step, not a judgment call made under time pressure.

## Rule 1 — Never discard or overwrite Zhenia's manual work

Before any script that closes, rebuilds, or saves over an open or saved .ai
file: check `doc.saved` and the file's on-disk mtime. If anything in the file
was not written by this session, stop and ask Zhenia before proceeding.

### ai_guard.jsx — the guard helper

Call this before any close, rebuild, or save-over. It is read-only by
default (`opts.write` is `false` unless set): calling it only checks state
and tells you whether it's safe to proceed, and it only writes the `_oldNN`
backup when you explicitly pass `write: true`, once you're ready to act on
an `ok: true` result.

`sessionLastWriteMs` is the epoch-ms time this session itself last wrote the
target file, or `0` if it never did — ExtendScript has no notion of "which
session," so the calling script (the Python/bash wrapper around `osascript`)
is responsible for tracking that and passing it in.

```javascript
// ai_guard.jsx — single check-and-backup guard for any close/rebuild/save-over.
// Refuses (ok:false) on unsaved changes or a file touched outside this
// session; only writes the _oldNN backup when opts.write is explicitly true.
// Returns a pipe-delimited string (ExtendScript/ES3 has no JSON.stringify).
function aiGuard(targetPath, opts) {
    opts = opts || {};
    var write = (opts.write === true);
    var approved = (opts.approved === true);
    var sessionLastWriteMs = opts.sessionLastWriteMs || 0;

    var ok = false, reason = "", open = false, saved = "", mtimeMs = "", backedUp = false;

    var openDoc = null;
    for (var i = 0; i < app.documents.length; i++) {
        if (app.documents[i].fullName.fsName === targetPath) {
            openDoc = app.documents[i];
            break;
        }
    }
    open = !!openDoc;
    if (openDoc) saved = openDoc.saved;

    var f = new File(targetPath);
    var existsOnDisk = f.exists;
    if (existsOnDisk) mtimeMs = f.modified.getTime();

    // Next backup name: highest existing _oldNN, plus one -- never fill an
    // earlier gap. A gap (e.g. _old02 missing between _old01 and _old03) may
    // be a backup someone deleted on purpose; reusing that number overwrites
    // whatever took its place conceptually. Computed regardless of outcome.
    var base = targetPath.replace(/\.ai$/i, "");
    var highest = 0;
    for (var n = 1; n <= 99; n++) {
        var suffix = (n < 10 ? "0" + n : "" + n);
        if ((new File(base + "_old" + suffix + ".ai")).exists) highest = n;
    }
    var nextSuffix = (highest + 1 < 10 ? "0" + (highest + 1) : "" + (highest + 1));
    var candidate = base + "_old" + nextSuffix + ".ai";

    // doBackup never trusts a bare .copy() call -- a failed copy must
    // produce ok:false, never a silent "backed up" claim that isn't true.
    function doBackup() {
        if (!existsOnDisk) return true; // nothing on disk to protect
        try {
            return !!f.copy(candidate);
        } catch (e) {
            return false;
        }
    }

    if (approved) {
        // Zhenia explicitly said "replace it": their on-disk version is
        // backed up first, unconditionally -- this path skips the unsaved/
        // mtime refusals below because they are the one overriding them, not
        // the script deciding it's fine. Approval is not license to skip
        // the backup itself: a failed copy still refuses.
        backedUp = doBackup();
        if (backedUp) {
            ok = true;
        } else {
            reason = "approved, but backup copy to " + candidate + " failed -- refusing";
        }
    // Refuse: unsaved changes in an open document.
    } else if (openDoc && openDoc.saved === false) {
        reason = "unsaved changes in open document";
    // Refuse: mtime check applies whether the doc is open or closed -- an
    // open, saved document can carry a save from a minute ago the session
    // never made, so saved:true alone is not enough to proceed.
    } else if (existsOnDisk && !sessionLastWriteMs) {
        reason = "session has no record of writing this file; mtime cannot be verified";
    } else if (existsOnDisk && mtimeMs > sessionLastWriteMs) {
        reason = "file mtime newer than the session's last write";
    } else if (write) {
        backedUp = doBackup();
        if (backedUp) {
            ok = true;
        } else {
            reason = "backup copy to " + candidate + " failed -- refusing";
        }
    } else {
        ok = true;
    }

    return "ok:" + ok + "|reason:" + reason + "|open:" + open + "|saved:" + saved +
           "|mtime_ms:" + mtimeMs + "|next_backup:" + candidate + "|backed_up:" + backedUp +
           "|approved:" + approved;
}

aiGuard("TARGET_PATH", {write: false, sessionLastWriteMs: 0});
```

The last statement's value is what `do javascript file` returns to
osascript's stdout — `$.writeln()` goes to the ESTK console instead and the
session never sees it. Don't wrap the final call in `$.writeln`, and apply
the same rule to any other snippet meant to report back: the last
expression is the only output osascript gets.

Run it via `osascript` (do not open the file first — the guard checks
`app.documents` for an already-open doc and the filesystem for a closed
one):

```bash
osascript -e 'tell application "Adobe Illustrator" to do javascript file "/tmp/ai_guard.jsx"'
```

### Decision rule

Call `aiGuard` with `write: false` first and read the result:

- `ok:false` → **stop and ask Zhenia** before closing, saving over, or
  rebuilding anything. `reason` tells you which: unsaved changes in the open
  document, no session record of writing the file, or an mtime newer than
  the session's last write.
- `ok:true` → every change since the last known-good state is one the
  session itself made in this run. Safe to proceed.

### Before replacing a file: _oldNN backup

Once `aiGuard` returns `ok:true` and the script is about to replace or save
over the file (not just a straight re-save — a rebuild, a save-as-over-
original, or anything that could lose the current on-disk content), call it
again with `write: true` to take the `_oldNN` backup before touching the
file. Do this even when the script is confident the rebuild is correct — the
backup is the recovery path if it isn't. Check `backed_up:true` in the
result before proceeding — `write:true` with a failed copy returns
`ok:false`, not a silent skip of the backup.

### "Approved by Zhenia" mode — they said replace it

When Zhenia has explicitly said to go ahead and replace the file (not a
script inferring it's fine), call `aiGuard(path, {write: true, approved:
true, sessionLastWriteMs: ...})`. This mode always takes the `_oldNN` backup
of whatever is currently on disk — their version — first, regardless of the
unsaved-changes or mtime checks above, because they're the one overriding
them. A failed backup copy still returns `ok:false`; approval overrides the
refusal checks, never the backup step itself. Only proceed with the
replace once the result shows both `ok:true` and `backed_up:true`.

### Closing documents

`doc.close(SaveOptions.DONOTSAVECHANGES)` is only ever correct for a
document **the session itself created in the current run** — never for a
document Zhenia already had open or saved, in any of these forms:

- **It looks unmodified right now** (`doc.saved === true`). A pre-existing
  document with nothing pending to save is still not the session's to
  discard — "nothing lost right now" isn't the test; "did this session
  create it" is. `doc.saved === true` on a document the session didn't
  create still closes via `SAVECHANGES` below, never `DONOTSAVECHANGES`.
- **The task says to discard it or "start clean."** A request to close a
  document and reopen it fresh doesn't make `DONOTSAVECHANGES` the right
  tool for a document the session didn't create — "clean" means closing it
  without losing anything, which is `SAVECHANGES` (after a backup) or
  leaving it open, not discarding.
- **The session just saved it as part of this task.** Calling `doc.save()`
  during the task doesn't retroactively make the session the document's
  creator; the same backup-then-`SAVECHANGES` path still applies.

For a document the session *did* create this run, also confirm `doc.saved
=== true` immediately before the close call — unsaved changes mean it
isn't safe to discard either, session-created or not.

For any document the session didn't create, call `aiGuard` with `write:
true` (or `approved: true` if Zhenia said to go ahead) to take the
`_oldNN` backup first — `SAVECHANGES` on a document the session didn't
create can overwrite whatever Zhenia's file held. Check the result for
`backed_up:true` before calling `SaveOptions.SAVECHANGES` — a result with
`backed_up:false` (whether `ok:false` from a refusal, or an approved call
whose copy failed) means stop, don't save over the file; the only
recovery copy didn't get made. Use `SaveOptions.SAVECHANGES` once the
backup is confirmed, or leave the document open for Zhenia instead of
guessing.

### Recording sessionLastWriteMs

Capture `sessionLastWriteMs` as `Date.now()` immediately after each `doc.
save()` the session itself performs — not once at session start, and not
only before the first write. Every subsequent `aiGuard` call in the same
session should pass the most recent of these timestamps, so the mtime
check reflects the session's actual last write rather than a stale
reference point from before several saves happened.

### Prefer editing named objects in place over rebuilding

Rebuilding a file from a script re-creates every object, which is exactly
how manual edits get silently discarded — the rebuilt version simply doesn't
contain them. Prefer finding and editing the specific named object instead:

```javascript
var doc = app.activeDocument;
var target = null;
for (var i = 0; i < doc.pageItems.length; i++) {
    if (doc.pageItems[i].name === "TARGET_OBJECT_NAME") {
        target = doc.pageItems[i];
        break;
    }
}
if (target) {
    // modify target in place — position, text content, fill color, etc.
} else {
    // object not found: stop and ask, don't fall back to a full rebuild.
}
```

A rebuild is sometimes genuinely the right tool (e.g. the document really
doesn't exist yet). When it is, Rule 1's preflight and backup steps still
apply to whatever file it's replacing.

## Rule 2 — Apply only the changes Zhenia asked for

No restyling, font-weight, color, or layout changes that weren't requested —
even when a design guideline (e.g. [[pi-design-system]]) seems to call for
one. If applying the design system's rules would also mean changing
something Zhenia didn't ask about, flag the conflict in chat instead of
silently "fixing" it. The literal request wins; the design system is for
new work, not for relitigating existing output.

## Rule 3 — PI files use the brand palette as global swatches, in two groups

Every Pilot Institute file uses the brand palette as **global swatches** —
every fill, stroke, text color, and gradient stop is linked to those
swatches, never to loose CMYK values. Source:
`~/dev/dev-PI/PI-design-system/colour-palette/` (on Zhenia's Mac, not this
box — don't guess the CSV's column layout; read the header row and stop
with a clear message if it has no name, color, and section columns, rather
than assuming a shape). Manually, appending `pilot-institute-colors.ase`
brings the swatches in as global already, already split into the two
folders below; scripting has no ASE import, so a script creates them from
`PI-Colour-Palette.csv` instead, reading the CSV's section column to sort
each color into the matching group.

This is Rule 1 and Rule 2 territory too: run `aiGuard` first like any other
script that touches the file, and this rule governs color only — it's not
license to make any other change while in there.

**Check the swatches on every PI file the routine opens.** Before any color
work, read the document's swatch groups: they must be exactly `PI-primary`
(25) and `PI-secondary` (30). If they are not, split the swatches per the
CSV sections (below) and add the missing colors; report what was added.

**Rule 3 also removes every swatch outside `PI-primary` / `PI-secondary`** —
default swatches, default groups, gradients, patterns — so the panel holds
only the two folders. Steps, in this order:

1. Relink every fill, stroke and gradient stop to the PI swatches: exact
   matches, and logo near-misses per "Logo colors" below.
2. Keep any gradient swatch still used by objects. Deleting an in-use
   gradient swatch strips the gradient and the object goes black;
   `app.undo` does not restore it.
3. Delete the rest.
4. Diff a before/after render (export per the Exports section, hide the
   `safe zone` layer first).

Hidden layers can't be edited by script, so relink cannot reach them:
unhide them, or report them.

### Exactly two swatch groups, matching the .ase file

`pilot-institute-colors.ase` ships exactly two folders — never one group
per CSV section, and never a single combined group:

- **PI-primary** (25 colors) — CSV sections `Primary Surfaces (Dark Mode)`,
  `Primary Interactive`, `Light Surfaces (Editorial / Print)`, `Text`.
- **PI-secondary** (30 colors) — CSV sections `Semantic States`,
  `Illustration & Chart Accents` (this section includes Logo Navy and Logo
  Ice Blue).

A script sorts each row into PI-primary or PI-secondary by its section
value, read from the CSV header — not a hard-coded column index. If a
row's section isn't one of these six names, or the final count in either
group isn't exactly 25 or 30, **stop and report the mismatch** instead of
guessing where the color belongs or proceeding with a wrong count — an
unrecognized section name most likely means the CSV changed and this
mapping needs updating first, not a script inventing a new group to put it
in.

### Reading the CSV

```javascript
var lines = File(csvPath).open("r") ? csvFile.read().split("\n") : null;
var header = lines[0].split(",");
var nameCol = header.indexOf("name");       // exact column names depend on
var colorCol = header.indexOf("cmyk");      // the real file -- these are
var sectionCol = header.indexOf("section"); // placeholders
if (nameCol === -1 || colorCol === -1 || sectionCol === -1) {
    throw new Error("PI-Colour-Palette.csv has no name/color/section column "
        + "in its header row (saw: " + header.join(", ") + ") — stop, don't guess");
}
```

### Creating the swatches (skip duplicates on re-run)

A script creates each color as `doc.spots` with
`colorType = ColorModel.PROCESS` (global process), named exactly as the CSV
`Name` column (`Sky Blue`, the same names the `.ase` ships), in
whichever of the two groups its CSV section maps to — but only if that name
doesn't already exist, so re-running the script never creates duplicates.
Look up by name with `getByName` first (the real Illustrator API throws if
the name isn't found — don't loop and compare `.name` by hand, catch the
throw instead):

```javascript
var PRIMARY_SECTIONS = ["Primary Surfaces (Dark Mode)", "Primary Interactive",
    "Light Surfaces (Editorial / Print)", "Text"];
var SECONDARY_SECTIONS = ["Semantic States", "Illustration & Chart Accents"];

function groupNameForSection(section) {
    for (var i = 0; i < PRIMARY_SECTIONS.length; i++) {
        if (PRIMARY_SECTIONS[i] === section) return "PI-primary";
    }
    for (var j = 0; j < SECONDARY_SECTIONS.length; j++) {
        if (SECONDARY_SECTIONS[j] === section) return "PI-secondary";
    }
    return null; // not one of the six known sections -- don't guess
}

function getOrAddGroup(groupName) {
    try {
        return doc.swatchGroups.getByName(groupName);
    } catch (e) {
        var g = doc.swatchGroups.add();
        g.name = groupName;
        return g;
    }
}

// For each row in PI-Colour-Palette.csv:
var groupName = groupNameForSection(row.section);
if (groupName === null) {
    throw new Error("PI-Colour-Palette.csv row '" + rowName + "' has section '"
        + row.section + "', not one of the six known sections -- stop, "
        + "don't guess which swatch group it belongs in");
}
var group = getOrAddGroup(groupName);
var swatchName = rowName;                     // e.g. "Sky Blue" -- the CSV name, as in the .ase
var spot;
try {
    spot = doc.spots.getByName(swatchName);   // already exists -- skip re-creating it
} catch (e) {
    spot = doc.spots.add();
    spot.name = swatchName;
    spot.colorType = ColorModel.PROCESS;   // global process color, not a spot ink
    spot.color = cmykColorFromRow(row);    // CMYK values from the CSV row
    group.addSpot(spot);
}
```

### Checking the final counts

After processing every row, count the spots in each group and stop if
either doesn't match the expected split — don't report the swatches done
with a wrong count:

```javascript
var primary = doc.swatchGroups.getByName("PI-primary");
var secondary = doc.swatchGroups.getByName("PI-secondary");
if (primary.spots.length !== 25 || secondary.spots.length !== 30) {
    throw new Error("swatch group counts don't match the expected 25/30 "
        + "split (got PI-primary:" + primary.spots.length + " PI-secondary:"
        + secondary.spots.length + ") -- stop, the CSV may have changed");
}
```

### Reassigning existing colors

Reassign matching fills, strokes, text colors, and gradient stops via
`SpotColor` with `tint` 100, not by editing the CMYK values directly — that
keeps the link to the global swatch:

```javascript
var sc = new SpotColor();
sc.spot = spot;   // the doc.spots entry created or found above
sc.tint = 100;
pageItem.fillColor = sc;  // or .strokeColor, or a TextRange's characterAttributes.fillColor
```

Gradient stops keep their opacity when you change their color — only swap
`gradientStop.color`, never touch `gradientStop.opacity` as part of a
recolor.

### Logo colors — near-misses relink automatically, don't flag

Color inside logo artwork specifically (not the rest of the document) often
drifts by a point or two of CMYK from a scan or a prior export — e.g.
`30/4/0/0` where the palette's Logo Ice Blue is `28/13/0/0`. For the four
logo-related swatches — **Logo Ice Blue**, **Logo Navy**, **Sky Blue**,
**Magenta Pink** — a near-miss found inside logo artwork is relinked to the
matching swatch directly (the same `SpotColor`/tint-100 reassignment as an
exact match), not added to the off-palette list below. This is the one
exception to "report a mismatch instead of changing it"; it's scoped
tightly — only these four swatches, only colors inside logo artwork, never
elsewhere in the document.

### When a color doesn't match

Change nothing that doesn't match the palette, with the one exception
above. Collect those colors into a list and return it, so the caller
reports the list in chat instead of the script silently fixing or skipping
past it — Rule 2 applied to color specifically: a mismatch is a conflict to
flag, not a bug to resolve on its own.

## Rule 4 — every new PI file copies the reference file's setup

Before any design work on a new PI Illustrator file, this is a **mandatory
first step**, not a background assumption — follow it in order:

1. **Open the reference read-only.** `BR-0027 CFI Program`,
   `Brochures/BR-0027 CFI Program/2. Design/261015_BR-0027 CFI Program.ai` —
   no save, and close it with `SaveOptions.DONOTSAVECHANGES` (never a save-on-
   close), since the session only reads it, never edits it. Rule 1's
   `aiGuard` checks still apply to this file the same as any other — opening
   it read-only doesn't exempt it. The reference stays on Zhenia's Mac: no
   copy is fetched to this box, and no `.ai` file is touched by this step.
2. **Read its setup.** The layer stack and each layer's hidden/locked/color
   state, the artboard and bleed, the swatches, and the grid.
3. **Reproduce them** in the new file:
   - **Layer order (top to bottom):** `ref` (guides and references,
     visible, unlocked), `bleed` (hidden by default, locked), `trash`
     (hidden by default, unlocked, black layer color), `Content`, `BG`
     (locked) — Rule 5 below. A Vistaprint A-frame file adds `safe zone`
     between `ref` and `bleed`.
   - **Safe zone layer (Vistaprint A-frame only):** non-printing, locked,
     one rectangle stroked 1 pt PI Cool Gray, 50% opacity, 4/4 pt dashes,
     74.5 pt in from the bleed edge. Hide it before any export — it renders
     in PNG exports. All guides share one color, so a guide in a different
     color is a stroked path on this layer, not a guide.
   - **Bleed layer:** grey strips covering the bleed outside the trim,
     filled with the pasteboard grey CMYK `57.40/47.02/46.31/36.15`; hidden
     by default — Zhenia toggles it on to preview the trim.
   - **Trash layer:** hidden by default, unlocked, black layer color — a
     holding place for removed objects, not deletion, so nothing a script
     pulls out of the design is gone for good.
   - **Artboard:** at trim size, with the artwork running into the bleed.
   - **Colors:** the brand palette as global swatches (Rule 3).
   - **Blueprint grid:** fading out top to bottom.
4. **List what couldn't be reproduced.** If the reference does something a
   script can't replicate, say so in chat instead of approximating it —
   don't invent a different structure, colors, or helper layers as a
   substitute.

The reference is the only source of truth for file setup, not a design
instinct or a guideline.

## Rule 5 — one five-layer stack in every Illustrator file; grids are guides on `ref`

Zhenia's rule (2026-10-28): every Illustrator file, print or digital, uses
the same layer structure as the brochure files. A script never adds a
main layer of its own (`grid`, `Layer 1`, `boxes` …) and never draws
grids or column lines as filled or stroked rectangles.

Top to bottom, exact names (case included), nothing outside them:

| Layer | Holds | Default state |
|---|---|---|
| `ref` | Every guide and reference object, on top of everything: column grids, content margins, trim / safety / fold guides, printer marks. Named guide sets go in sub-layers of `ref` | Visible, unlocked |
| `bleed` | Grey shapes that block off every area not visible in the final work (pasteboard grey, Rule 4). **Print:** the artboard is the bleed box and the grey blocks sit inside it, covering what is cut off after printing. **Digital:** grey frames around the artboard, outside it, so nothing that falls past the screen edge shows | Hidden by default, locked; Zhenia toggles it to preview |
| `trash` | Holding place for objects pulled out of the design, never deletion | Hidden, unlocked, black layer colour |
| `Content` | The typography and the images that sit on top of the background | Visible, unlocked |
| `BG` | What sets the tone of the background: solid-colour shapes and solid-colour display text | Locked |

- **Grids and column lines are Illustrator guides** (`pathItem.guides =
  true`) on `ref`, never rectangles with a fill or stroke, and never on a
  new layer. Draw the path on `ref`, then set `guides = true`; a snapping
  tab outside the artboard is a guide too.
- **Column snapping tabs sit above *and* below every artboard**, one per
  column, column-width (197 px on the 1302 px web grid), 8 px tall, named
  `col n tab` / `col n tab bottom`. Keep a **48 px clear gap** between the
  tab and the artboard edge (tab bottom 48 px above the top edge, tab top
  48 px below the bottom edge): Illustrator draws the artboard name label
  just above the top edge, and tabs closer than that cover it (Zhenia,
  2026-10-28; 16 px overlapped the label). Position with `item.top`, not
  `translate()`.
- A file that lacks one of the five gets that exact layer added in its
  place. A stray layer is merged into the layer its content belongs to
  (`templates/CREATING-TEMPLATES.md` in PI-design-system has the merge
  script) — but only when Zhenia asks for the restructure (Rule 2).
- Record: on 2026-10-28 a session put the course-page column grid on a new
  `grid` layer as 12 % cyan rectangles in `261027_course-pages-3.ai`. That
  is the wrong shape; it is to become guides on `ref` on Zhenia's signal.

## Exports — approval PDFs, test PDFs, and verifying the output

### Before any export

Hide the `bleed` and `trash` layers (Rule 4) before exporting anything —
both are part of Zhenia's working view, not what ships.

### Export from the saved file, never `saveAs` the open working doc

Generate PDFs from the saved `.ai` file — never `saveAs` the open working
document directly to a PDF. `saveAs` retargets the open document to the PDF
file itself, so the document's next `doc.save()` in the session would
overwrite the PDF instead of the `.ai` file.

### Two PDF types, two different page structures

- **Vistaprint test PDFs** — CMYK, PDF/X-4, with bleed, **one PDF per
  artboard**.
- **Approval PDFs** — RGB, at trim size (no bleed), **one PDF, one page
  per artboard**.

### Approval PDFs: PNG24 → assemble is the only correct path

Two paths that look plausible are both known-bad, not occasional glitches
— don't reach for either:

- Illustrator's own PDF export throws MRAP when asked to convert color to
  RGB.
- Routing an Illustrator-exported CMYK PDF through Ghostscript
  (`gs ... -sColorConversionStrategy=RGB`) flattens any transparent
  gradient (gradient stops with opacity) into a solid fill.

The only path that preserves gradients and transparency correctly:

1. `exportFile` each artboard as PNG24 at 150 ppi from the saved `.ai`.
2. Crop each PNG to the trim size (no bleed).
3. Assemble the cropped PNGs into one PDF at trim size — one PDF total,
   one page per artboard.

### Verify before reporting an export done

Show them side by side: after every export — either type — render each
output page, in its actual color space, next to Illustrator's own PNG24
export of the same artboard from the saved `.ai`, and compare them. Any
visible difference in gradients, transparency, color, or crop means the
export failed. A failed export is never reported as done.

## Known ExtendScript / osascript gotchas

- **`translate()` / `duplicate()` + move drops opacity masks.** Objects moved
  by script keep their mask attached to the old position, so masked images
  render blank (261026 course cards). Copy/paste in place keeps masks; a manual
  move in the UI does too. To duplicate an artboard's content by script:
  `selectObjectsOnActiveArtboard` → `app.copy()` → activate the new artboard →
  `executeMenuCommand("pasteInPlace")`, no translate afterwards.
- **`executeMenuCommand("pasteInPlace")` pastes a copy on every artboard**
  (observed in Illustrator 30: one copy per artboard, including a copy stacked
  on the source). Remove the other artboards before the paste and re-add them
  at their saved `artboardRect`, then delete the stray copy that lands back on
  the source by z-order (pasted items are the top N of the layer) and position.
- **`app.copy()` / paste need Illustrator frontmost** (error 9002). Run
  `tell application "System Events" to set frontmost of process "Adobe
  Illustrator" to true` and wait 2 s before the script; `activate` alone was
  not enough.
- **Canvas limit:** `artboardRect` or `artboards.add` beyond roughly ±8191 pt
  from the document's original centre throws `CoOA` (1095724867). Parking an
  artboard "far away" is not an option.
- **`selectObjectsOnActiveArtboard` can select more than copy/paste carries**
  (3149 selected, 3145 pasted on a saved-clean doc); compare pasted counts
  with a tolerance, not equality.
- **`doc.save()` on an .ai with linked PNGs grew the file 31 → 150 MB** (PDF
  compatible stream renders the links); expect it, and mention the size.
- **Cross-document `duplicate()` of blend PluginItems throws MRAP.** Use
  `app.copy()` then `app.paste()` into the target document instead — it goes
  through the clipboard rather than the object model and doesn't hit the
  same error.
- **Repeated MRAP errors on text attributes clear after restarting
  Illustrator.** If a script starts throwing MRAP on text attribute access
  mid-session with no code change, that's accumulated app state, not a bug
  in the script — restarting Illustrator before the next run is the fix.
- **`executeMenuCommand('makeMask')` makes a clipping mask, not an opacity
  mask.** If the task needs an opacity mask, this call is the wrong tool —
  don't use it and assume it did what an opacity mask would.
- **Area type cut exactly at the last baseline drops the line.** When
  calculating where to cut an area-type frame, add 0.01 pt to the cut point
  so the last line of text isn't silently dropped.
- **Ghostscript's `-sColorConversionStrategy=RGB` flattens transparent
  gradients into solid fills.** Gradient stops with opacity lose that
  transparency when a CMYK PDF is converted to RGB this way — don't route
  an export through it (see Exports).
- **Illustrator's own PDF color conversion throws MRAP.** Asking
  Illustrator to export a PDF directly converted to RGB fails this way
  rather than producing a usable file (see Exports).
- **Illustrator 30.7 crashes (SIGSEGV in `LiveObjectProperty::get`) on
  text-attribute reads.** Two crashes came from scripts reading
  `characterAttributes`, `paragraphAttributes`, `leading`, or `size`. Avoid
  every text-attribute read. Safe: `lines.length`, `contents`, `anchor`,
  `textPath.pathPoints`, `duplicate().createOutline()`. To copy a text
  style, duplicate a styled frame, set its `contents`, and translate it to
  the original's `anchor`.
- **Test a new approach on a scratch copy opened as its own document,
  then apply it once to Zhenia's doc.** Never trial-and-error on the live
  file (Rule 1).
- **`layer.move()` throws 9024 "Cannot modify a layer that is locked" when
  the moved layer or the reference layer is hidden**, not only when locked
  (261028, `trash` and `bleed`). Unhide both for the move, then re-hide and
  re-lock; and re-check every lock state afterwards, since a failed run
  leaves whatever it had already unlocked.
- **No chained ternaries.** `a ? 4 : b ? 6 : 0` misbehaved in ExtendScript;
  write plain `if` statements.
- **Illustrator's y axis is up-positive.** Moving up is `+dy`.
- `tools/on-demand/yt-autopilot/illustrator-placement-brief.md` has more
  ExtendScript caveats worth reading before a larger placement script: no
  `JSON` object in ExtendScript (ES3), AppleEvent timeout defaults to 120s
  (wrap in `with timeout of 600 seconds` for batch ops), dedup must check
  each file path individually rather than a blanket "anything placed?"
  check, and `var` has function-level scope only (watch loop variable
  collisions).

### Area type: fit the frame to its last baseline

To resize an area-type frame so it ends on the text's last baseline:

1. **Measure from an outlined duplicate** (`duplicate().createOutline()`),
   never the live frame. Take the bottom of each glyph on the last line,
   bucket the values within ±0.75 pt, take the most common bucket, and use
   its highest value as the last baseline.
2. **Don't swap the last line for "H" to measure it.** The swap reflows the
   text onto the previous line.
3. **Resize by moving the bottom `textPath.pathPoints`.** After each move,
   check `lines.length` is unchanged; if not, step +0.25 pt up, to a
   maximum of 1 pt, and if it still differs, revert the move.
4. **A one-line area frame becomes point type** instead of being fitted.

## Templates

Creating or updating a file in the design system's `templates/` folder, or
setting up any new PI Illustrator or InDesign file, starts with
`tools/PI-design-system/templates/CREATING-TEMPLATES.md` (pi-bench): the
five-layer structure (`bleed`, `ref`, `trash`, `Content`, `BG`), the two
swatch folders, and the fix scripts in `templates/_scripts/`. Rules 1 to 4
above still govern how a script touches the file.

## Related

- [[pi-design-system]] — brand design system. Rule 2 above wins when it
  conflicts with a design-system instinct to "complete" a design.
- `tools/on-demand/yt-autopilot/illustrator-placement-brief.md` — a working
  consolidated-placement JSX script (open, dedup, place, save, close) for
  a larger worked example of the open/close/save lifecycle these rules
  guard.
