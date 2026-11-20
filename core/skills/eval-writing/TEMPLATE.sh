#!/usr/bin/env bash
# Done when: <one checkable gate: the target, the number it expects, and how it is read (exit 0 = true)>
#
# evals/<TICKET-KEY>.sh — <title> (<TICKET-KEY>)
# Everything below the opener says what the gate leaves open: checks, fixtures, safety.
#
# §0 Safety — read-only; this eval makes no write call to the live target
# §1 <check> — <exact result that passes>
#
# Run: bash evals/<TICKET-KEY>.sh
set -u
PASS=1
fail() { echo "FAIL: $1"; PASS=0; }
ok()   { echo "ok:   $1"; }

# ... checks against the real target ...

[ "$PASS" = 1 ] && exit 0 || exit 1
