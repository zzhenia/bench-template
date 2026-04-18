#!/usr/bin/env python3
"""
Actions Dashboard — local HTTP server on port 7391.
Auto-discovers actions from the folder structure, reads bench-index.csv
for ticket links, and streams action output inline via SSE.
"""

import csv
import json
import socketserver
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parents[3]
PORT = 7391

# ── Auto-discovery ───────────────────────────────────────────────────────────

SKIP_FOLDERS = {"dashboard", "actions-dashboard", "~archive", "~empty", "Templates"}
RUN_PATTERNS = ["run.sh", "*.py"]


def load_keys():
    keys = {}
    kf = BASE / "config" / "keys.env"
    if kf.exists():
        for line in kf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                keys[k.strip()] = v.strip()
    return keys


def load_index():
    index_file = BASE / "bench-index.csv"
    if not index_file.exists():
        return {}
    lookup = {}
    with open(index_file, newline="") as f:
        for row in csv.DictReader(f):
            af = row.get("action_folder", "").strip()
            if af:
                lookup[af] = row
    return lookup


def find_run_cmd(folder: Path) -> str | None:
    """Find the best runnable script in an action folder."""
    # Prefer run.sh if it exists
    run_sh = folder / "run.sh"
    if run_sh.exists():
        return f"bash {run_sh}"
    # Look for a top-level .py file (skip __init__.py, test files)
    py_files = sorted(
        p for p in folder.glob("*.py")
        if p.name not in ("__init__.py",) and not p.name.startswith("test_")
    )
    if py_files:
        return f"python3 {py_files[0]}"
    return None


def read_desc(folder: Path) -> str:
    """Read the first non-heading, non-empty line from instructions.md as the description."""
    inst = folder / "instructions.md"
    if not inst.exists():
        return ""
    for line in inst.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            return line
    return ""


def discover_actions():
    """Scan actions/ for on-demand and recurring action folders."""
    index = load_index()
    actions = []

    for section, section_type in [("on-demand", "on-demand"), ("recurring", "recurring")]:
        section_dir = BASE / "actions" / section
        if not section_dir.is_dir():
            continue
        for folder in sorted(section_dir.iterdir()):
            if not folder.is_dir() or folder.name in SKIP_FOLDERS:
                continue
            action_path = f"actions/{section}/{folder.name}"
            idx_row = index.get(action_path, {})
            run_cmd = find_run_cmd(folder)
            desc = read_desc(folder)

            actions.append({
                "id": folder.name,
                "name": folder.name.replace("-", " ").title(),
                "type": section_type,
                "desc": desc,
                "folder": action_path,
                "run": run_cmd,
                "jira": idx_row.get("jira", "").strip() or None,
                "asana": idx_row.get("asana", "").strip() or None,
            })
    return actions


# ── HTML ─────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__DASHBOARD_TITLE__</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {
    --bg: #1a1a1a;
    --surface: #242424;
    --border: #333;
    --text: #e8e8e8;
    --muted: #888;
    --accent: #5b9cf6;
    --green: #4caf7d;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 14px; padding: 32px 32px 60px; }
  h1 { font-size: 20px; font-weight: 600; margin-bottom: 6px; }
  .subtitle { color: var(--muted); font-size: 13px; margin-bottom: 28px; }
  .section-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin: 28px 0 10px; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; padding: 6px 12px; border-bottom: 1px solid var(--border); }
  td { padding: 11px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--surface); }
  .name { font-weight: 500; white-space: nowrap; }
  .desc { color: #bbb; font-size: 13px; line-height: 1.5; max-width: 440px; }
  .links { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .btn-play {
    display: inline-flex; align-items: center; gap: 5px;
    background: var(--green); color: #fff; border: none; border-radius: 5px;
    padding: 5px 11px; font-size: 12px; font-weight: 600; cursor: pointer;
    transition: opacity .15s;
  }
  .btn-play:hover { opacity: .85; }
  .btn-play:disabled { background: #444; color: #666; cursor: not-allowed; }
  .btn-play svg { width: 10px; height: 10px; fill: currentColor; }

  #terminal {
    display: none;
    margin-top: 28px;
    border: 1px solid var(--border);
    border-radius: 7px;
    overflow: hidden;
  }
  .term-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  #term-title { font-size: 12px; color: var(--muted); }
  .btn-clear {
    background: none; border: 1px solid var(--border); border-radius: 4px;
    color: var(--muted); cursor: pointer; font-size: 11px; padding: 2px 8px;
  }
  .btn-clear:hover { color: var(--text); border-color: #555; }
  #term-output {
    font-family: "SF Mono", "Menlo", "Monaco", monospace;
    font-size: 12px; line-height: 1.6; color: #ccc;
    background: #0e0e0e;
    padding: 14px 16px;
    min-height: 80px; max-height: 340px;
    overflow-y: auto;
    white-space: pre-wrap; word-break: break-all;
  }
  .term-done  { color: var(--green); }
  .term-error { color: #e06c6c; }
  .footer { margin-top: 1.5rem; color: var(--muted); font-size: 0.75rem; }
</style>
</head>
<body>
<h1>__DASHBOARD_TITLE__</h1>
<p class="subtitle">Local automation hub — click Run to stream output below</p>

<div id="app"></div>

<div id="terminal">
  <div class="term-header">
    <span id="term-title"></span>
    <button class="btn-clear" onclick="clearTerminal()">Clear</button>
  </div>
  <div id="term-output"></div>
</div>

<p class="footer">Auto-discovered from actions/ folders. Updates automatically.</p>

<script>
let ACTIONS   = __ACTIONS_JSON__;
const JIRA_URL  = "__JIRA_URL__";

let currentStream = null;
let activeBtn     = null;
let activeBtnHTML = '';

function clearTerminal() {
  document.getElementById('term-output').innerHTML = '';
  document.getElementById('terminal').style.display = 'none';
}

function appendLine(text, cls) {
  const out = document.getElementById('term-output');
  const span = document.createElement('span');
  if (cls) span.className = cls;
  span.textContent = text + '\\n';
  out.appendChild(span);
  out.scrollTop = out.scrollHeight;
}

function runAction(id) {
  if (currentStream) { currentStream.close(); currentStream = null; }

  const action = ACTIONS.find(a => a.id === id);
  const terminal = document.getElementById('terminal');
  terminal.style.display = 'block';
  document.getElementById('term-output').innerHTML = '';
  document.getElementById('term-title').textContent = action?.name ?? id;

  if (activeBtn) { activeBtn.disabled = false; activeBtn.innerHTML = activeBtnHTML; }
  activeBtn = document.getElementById('btn-' + id);
  activeBtnHTML = activeBtn?.innerHTML ?? '';
  if (activeBtn) { activeBtn.disabled = true; activeBtn.textContent = '...'; }

  currentStream = new EventSource('/api/stream/' + id);
  currentStream.onmessage = (e) => {
    if (e.data === '__DONE__') {
      currentStream.close(); currentStream = null;
      appendLine('\\n Done', 'term-done');
      if (activeBtn) { activeBtn.disabled = false; activeBtn.innerHTML = activeBtnHTML; activeBtn = null; }
    } else if (e.data === '__ERROR__') {
      currentStream.close(); currentStream = null;
      appendLine('\\n Exited with error', 'term-error');
      if (activeBtn) { activeBtn.disabled = false; activeBtn.innerHTML = activeBtnHTML; activeBtn = null; }
    } else {
      appendLine(e.data);
    }
  };
  currentStream.onerror = () => {
    currentStream.close(); currentStream = null;
    appendLine('[connection lost]', 'term-error');
    if (activeBtn) { activeBtn.disabled = false; activeBtn.innerHTML = activeBtnHTML; activeBtn = null; }
  };
}

function renderSection(title, actions) {
  if (!actions.length) return '';
  const rows = actions.map(a => {
    const playBtn = a.run
      ? `<button class="btn-play" id="btn-${a.id}" onclick="runAction('${a.id}')">
           <svg viewBox="0 0 10 10"><polygon points="2,1 9,5 2,9"/></svg> Run
         </button>`
      : `<button class="btn-play" disabled title="No runnable script found">
           <svg viewBox="0 0 10 10"><polygon points="2,1 9,5 2,9"/></svg> Run
         </button>`;

    const jiraLink  = a.jira && JIRA_URL
      ? ` <a href="${JIRA_URL}/browse/${a.jira}" target="_blank" title="${a.jira}">Jira</a>`
      : '';

    return `<tr>
      <td><span class="name">${a.name}</span></td>
      <td><span class="desc">${a.desc}</span></td>
      <td><div class="links">${playBtn}${jiraLink}</div></td>
    </tr>`;
  }).join('');

  return `<p class="section-title">${title}</p>
<table>
  <thead><tr><th>Action</th><th>Description</th><th style="width:180px">Links</th></tr></thead>
  <tbody>${rows}</tbody>
</table>`;
}

function renderAll() {
  const onDemand  = ACTIONS.filter(a => a.type === 'on-demand');
  const recurring = ACTIONS.filter(a => a.type === 'recurring');
  document.getElementById('app').innerHTML =
    renderSection('On-demand', onDemand) +
    renderSection('Recurring', recurring);
}

// Initial render
renderAll();

// Poll for new actions every 3 seconds — re-render if changed
let lastSignature = JSON.stringify(ACTIONS.map(a => a.id).sort());
setInterval(async () => {
  try {
    const resp = await fetch('/api/actions');
    const fresh = await resp.json();
    const sig = JSON.stringify(fresh.map(a => a.id).sort());
    if (sig !== lastSignature) {
      ACTIONS = fresh;
      lastSignature = sig;
      renderAll();
    }
  } catch(e) {}
}, 3000);
</script>
</body>
</html>"""


# ── Server ───────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            actions = discover_actions()
            keys = load_keys()
            jira_url = keys.get("JIRA_URL", keys.get("ZV_JIRA_URL", ""))
            owner = keys.get("BENCH_OWNER", "").strip()
            title = f"{owner}\u2019s Actions Dashboard" if owner else "Actions Dashboard"
            actions_json = json.dumps(actions)
            page = (HTML
                    .replace("__DASHBOARD_TITLE__", title)
                    .replace("__ACTIONS_JSON__", actions_json)
                    .replace("__JIRA_URL__", jira_url))
            body = page.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/api/actions":
            actions = discover_actions()
            body = json.dumps(actions).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path.startswith("/api/stream/"):
            self._handle_stream(parsed)

        else:
            self.send_response(404)
            self.end_headers()

    def _handle_stream(self, parsed):
        action_id = parsed.path[len("/api/stream/"):]
        actions = discover_actions()
        action = next((a for a in actions if a["id"] == action_id), None)

        if not action or not action.get("run"):
            self.send_response(400)
            self.end_headers()
            return

        cmd = action["run"]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def sse(line):
            self.wfile.write(f"data: {line}\n\n".encode())
            self.wfile.flush()

        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in proc.stdout:
                sse(line.rstrip("\n"))
            proc.wait()
            sse("__DONE__" if proc.returncode == 0 else "__ERROR__")
        except (BrokenPipeError, ConnectionResetError):
            pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    server = ThreadedHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Bench Dashboard -> {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    server.serve_forever()
