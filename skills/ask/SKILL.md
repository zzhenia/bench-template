---
name: ask
description: Ask an OpenClaw agent (Eva, Kitty, Olga, …) running on the laptop gateway and relay the reply. Usage: /ask <agent> <message> — or /ask list to see the roster.
model: haiku
---

Talk to an OpenClaw agent running on the OpenClaw gateway. All agents share one gateway, so any agent — present or future — is reachable by id. The gateway URL is read from `~/.openclaw-remote.env` (`OPENCLAW_GATEWAY_URL`) — currently `ws://100.96.0.28:18789` (the gateway runs on Hetzner `openclaw-1` over Tailscale; this machine is a remote client). `scripts/oc-agent.sh` is the engine; this command just relays.

Steps:
1. Parse the argument:
   - `/ask list` → run `bash scripts/oc-agent.sh list` and show the roster.
   - `/ask <agent> <message>` → run `bash scripts/oc-agent.sh <agent> "<message>"`.
   - `/ask <message>` (no agent id) → run `bash scripts/oc-agent.sh "<message>"` (routes to DEFAULT_AGENT).
2. Relay the agent's reply to the user. The script's stdout IS the agent's response — show it, don't paraphrase.
3. On error:
   - `~/.openclaw-remote.env not found` → tell the user to copy `scripts/openclaw-remote.env.example` to `~/.openclaw-remote.env`, paste the gateway token, and `chmod 600` it.
   - `openclaw CLI not found` → tell them to run `npm i -g openclaw` once on this machine.
   - Connection refused / timeout → the gateway may be down; check it's running on openclaw-1 (`systemctl --user status openclaw-gateway`) and that `OPENCLAW_GATEWAY_URL` in `~/.openclaw-remote.env` matches where it's listening (currently `ws://100.96.0.28:18789`).

Notes:
- New agents added on the laptop appear automatically via `/ask list` — this command never needs editing to support one.
- Never paste the gateway token into chat or commit it. It lives only in `~/.openclaw-remote.env` (chmod 600).
- These are real agents with tools and memory; treat replies as coming from a teammate, and don't ask them to take destructive or outward-facing actions without the user's say-so.
