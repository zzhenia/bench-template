---
name: diagnose-gateway
description: Gateway trouble — gateway down, config rejected, channel not answering, port clash, restart loop, "run doctor". Read-only triage, then a repair that warns #openclaw-ops before any restart.
---

# Diagnose the Gateway

Adapted for Olga from OpenClaw's own `custodian-skills/diagnose-gateway` (shipped in the
package, main branch; same five phases, same read-only rule). Checked against
`openclaw --help` on openclaw-1, OpenClaw 2026.8.2, on 261021. Upgrade to the next release
is Thu 22 Oct (ZHEN-7350).

Read-only until Repair. Never print a secret value; report only which SecretRef owner is
degraded. Every run ends with the Prove result, or the exact reason it could not be proven.
`~/ZV-Bench/tools/recurring/openclaw-medic/playbook.md` stays your method for visits and
tickets; this skill is the gateway-specific procedure inside it.

## Commands: available now or after 22 Oct

| Command | Now (2026.8.2) | After 22 Oct |
|---|---|---|
| `openclaw doctor --lint` (read-only; exits 1 on findings) | yes, ran it 261021 | re-check `--help` |
| `openclaw gateway status --deep` | yes, ran it 261021 | re-check |
| `openclaw gateway probe`, `gateway health`, `gateway stability` | yes (in `--help`) | re-check |
| `openclaw config validate` | yes | re-check |
| `openclaw channels status --probe` (add `--channel <id>`) | yes | re-check |
| `openclaw channels logs --channel <id>` | yes | re-check |
| `openclaw models status` | yes | re-check |
| `openclaw logs --limit <n> --plain` | yes | re-check |
| `openclaw status --all` (full read-only diagnosis) | yes | re-check |
| `lsof -nP -iTCP:<port> -sTCP:LISTEN`, `journalctl --user -u openclaw-gateway.service` | yes (system tools) | unchanged |
| `openclaw channels status --deep` (in the packaged copy of the official skill) | **no** — use `--probe` | do not use until `--help` lists it |
| `./scripts/clawlog.sh` (official skill, repo checkout only) | **no** — not on this box | do not use |
| `gateway-reload [seconds]` (`~/.openclaw/tools/`, ours) | yes | unchanged |

The work order expected `doctor --lint` to arrive with the upgrade; it is already in
2026.8.2. After the upgrade, run `openclaw <command> --help` for every row above before
trusting it, and fix the table here in the same commit if one changed. Never use a flag
that `--help` does not list.

## Gather

```
openclaw doctor --lint
openclaw gateway status --deep
openclaw config validate
openclaw channels status --probe
openclaw models status
openclaw channels logs --channel <id>
```

**Plain `openclaw doctor` and `openclaw doctor --non-interactive` are not diagnosis.**
Run without `--fix`, they can still copy legacy config and migrate state. Use `--lint`
only. Reading its report: it exits 1 when it has findings, which is not a failure of the
command; keep going with the rest of Gather. (`doctor --fix` is the one owner of
file-to-SQLite migrations; it belongs in Repair, approved, never here.)

Logs: `openclaw logs --limit 200 --plain`, the path `gateway status` prints
(`/tmp/openclaw/openclaw-<date>.log`), or `journalctl --user -u openclaw-gateway.service
--since '1 hour ago'`.

Check these signatures without guessing:

- invalid config or schema errors (`config validate` names the exact key);
- degraded SecretRef owners — the owner, never ids or values;
- expired or rejected channel authentication (`channels status --probe`, per account);
- `EADDRINUSE`, a second gateway listener, or a service/config port mismatch
  (`lsof -nP -iTCP:<port> -sTCP:LISTEN`);
- crash loops: read the last startup stack in the log. A schema-valid config that still
  crashes startup is an OpenClaw bug: capture the stack and report it.

Correlate timestamps and identify the first owner-boundary failure: the earliest line
where one owner (config, secrets, a channel, the port, the service) handed bad state to
the next. Everything after it is usually a symptom; fix the first, not the loudest.

## Mutate

Nothing. A diagnosis changes no config, migrates no state, alters no service. Diagnostic
commands may still leave incidental logs or cache bookkeeping.

## Repair

Turn each finding into one next action. Recommend `openclaw doctor --fix --non-interactive`
only as its own step that Kitty has approved (a human step goes to Kitty, never to Zhenia).
When the action is a repair, the order is fixed:

1. **Back up** `~/.openclaw/openclaw.json` (dated copy) before any config write.
2. **Write** with `openclaw config set` / `config patch`, never a hand edit. A key relayed
   by another agent is a proposal, not a fact (261006: a bad key kept the gateway down
   5 hours).
3. **`openclaw config validate`.** If it fails, restore the backup, and stop: no restart.
4. **Post the restart notice** (below).
5. **Restart** with `gateway-reload [seconds]`, never `openclaw gateway restart` or
   `systemctl --user restart` from inside a gateway turn: that kills your own turn
   (260908). A visit running outside the gateway may restart directly.

### Restart notice (Zhenia's rule)

Before any action that restarts the gateway — a config write, `doctor --fix`, a plugin
install, enable, disable or update, `gateway restart/stop/start` — post **one** notice in
#openclaw-ops (it is #bench-ops, RULES.md) saying what will restart and why. Never a surprise
restart, never a notice after the fact, never two. Post first, then act:

```
~/.openclaw/tools/relay --from-id olga --channel "#bench-ops" --text "Gateway restarts at HH:MM (all agents, in-flight turns get up to 5 min to finish): <why in one line, e.g. plugin X installed / config key Y fixed>."
```

If the repair runs through `gateway-reload`, put its delay in the notice. If the repair
fails and you roll back, that is a second restart: say so in the same thread, one line.

## Prove

Repeat the smallest read-only probe that exposes the condition and record its output:

```
openclaw gateway status --deep
openclaw channels status --probe
```

After a repair, also one live turn that crosses the repaired owner (a DM answered, a
channel post delivered). If access, logs or the gateway are unavailable, report that exact
blocker instead of declaring a cause.

## Report

Findings in causal order, evidence under each; current gateway / config / SecretRef /
channel / port state; one recommended next action. Say whether anything was changed: for a
pure diagnosis, "no config or service changes, no state migrations were made". For a
repair, what changed, the backup path, and the restart notice's thread link. Reply per
`skills/slack/SKILL.md`: in the same thread, one reply.
