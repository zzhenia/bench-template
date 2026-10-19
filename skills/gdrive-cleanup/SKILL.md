---
name: gdrive-cleanup
description: Clean up Google Drive lost_and_found — rescue stranded files, delete junk temps and conflict copies.
model: sonnet
---

Clean up the Google Drive `lost_and_found` directory. Files end up here when sync fails (slow connection, interrupted uploads, conflicts). This skill triages every file: rescues anything missing from its destination, and deletes junk.

## Constants

```
LOST_FOUND=~/Library/Application Support/Google/DriveFS/lost_and_found/
DRIVE_BASE=~/Library/CloudStorage/GoogleDrive-zzhenia@gmail.com/My Drive/
```

## Procedure

### 1. Discover

List subdirectories under `$LOST_FOUND`. Each subdirectory is a Google account ID. For each one:

- Read `lost_and_found_data.txt` inside it. Each line is a comma-separated pair: `<original Drive path>, <lost_and_found path>`. This maps every stranded file to where it was supposed to live.
- List all files in the subdirectory with `ls -la` to get sizes and dates.

If `lost_and_found` is empty or doesn't exist, report "Nothing in lost_and_found" and stop.

### 2. Classify every file

For each file in `lost_and_found_data.txt`, classify it into one of three categories:

#### a) Temp / junk — safe to delete
- Illustrator temps: `~ai-*.tmp`
- Acrobat temps: `Acr*.tmp`
- Any other `.tmp` file
- macOS metadata: `.DS_Store`

#### b) Duplicate — already on Drive
Compare the stranded file against the file at the original Drive path:
- If the destination file exists AND has the **same size** (bytes), it's a duplicate. Mark for deletion.
- Files with numeric suffixes in parentheses like `(1784347877957)` are Drive conflict copies — also duplicates if the base file exists with the same or larger size.

#### c) Rescue — missing from Drive
If the destination file does **not** exist (or exists but has a different/smaller size), this file needs to be moved back.

### 3. Present the plan

Show a summary table to the user:

```
| File | Size | Category | Action |
|------|------|----------|--------|
| ... | ... | Temp | Delete |
| ... | ... | Duplicate (same 64MB on Drive) | Delete |
| ... | ... | Missing from Drive | Rescue → <dest path> |
```

Include totals: how many files to delete, how many to rescue, how much space freed.

Wait for user confirmation before proceeding. If they say "go" / "yep" / "do it" or similar, proceed. If they want to adjust, update the plan.

### 4. Execute

#### Rescue files
For each file marked "Rescue":
1. Check if a file already exists at the destination path.
2. If it does: rename the **existing** file with suffix `_oldNN` (glob for existing `_oldNN` files and use the next index number — never overwrite existing backups).
3. Move (`mv`) the stranded file to the destination path.

#### Delete junk and duplicates
Delete all files classified as Temp or Duplicate from `lost_and_found`.

#### Clean up
- If `lost_and_found_data.txt` is the only file remaining, delete it too.
- If the account subdirectory is now empty (or only has `lost_and_found_data.txt`), remove the subdirectory.

### 5. Report

Show a final summary:
- Files rescued (with destination paths)
- Files deleted (count + total size freed)
- Any errors encountered

## Rules

- Never delete a work file (.ai, .psd, .indd, .pdf, .png, .jpg, .mp4, etc.) unless a same-size copy is confirmed on Drive.
- When in doubt about whether a file is junk, ask — don't delete.
- Always use `_oldNN` suffix pattern for backup renames (glob for existing, increment).
- The `lost_and_found_data.txt` is the source of truth for original paths — always read it first.
