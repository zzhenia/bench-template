#!/usr/bin/env python3
"""
Actions Dashboard — local HTTP server on port 7391.
Reads from bench-index.csv and renders a dashboard page.
"""
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
PORT = 7391


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
        return []
    with open(index_file, newline="") as f:
        return list(csv.DictReader(f))


def build_html(rows, jira_url):
    def jira_link(key):
        if not key:
            return "—"
        url = f"{jira_url.rstrip('/')}/browse/{key}" if jira_url else "#"
        return f'<a href="{url}" target="_blank">{key}</a>'

    def asana_link(gid):
        if not gid:
            return "—"
        return f'<a href="https://app.asana.com/0/{gid}" target="_blank">{gid}</a>'

    rows_html = ""
    for r in rows:
        slug = r.get("slug", "")
        rtype = r.get("type", "")
        convo = r.get("convo_folder", "") or "—"
        action = r.get("action_folder", "") or "—"
        jira = jira_link(r.get("jira", "").strip())
        asana = asana_link(r.get("asana", "").strip())
        rows_html += f"""
        <tr>
          <td><strong>{slug}</strong></td>
          <td><span class="badge badge-{rtype}">{rtype}</span></td>
          <td class="mono">{convo}</td>
          <td class="mono">{action}</td>
          <td>{jira}</td>
          <td>{asana}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bench Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 14px;
      padding: 2rem;
    }}
    h1 {{
      color: #f0f6fc;
      font-size: 1.5rem;
      margin-bottom: 0.25rem;
    }}
    .subtitle {{
      color: #8b949e;
      margin-bottom: 2rem;
      font-size: 0.875rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #161b22;
      border-radius: 8px;
      overflow: hidden;
    }}
    th {{
      background: #21262d;
      color: #8b949e;
      text-align: left;
      padding: 10px 16px;
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    td {{
      padding: 10px 16px;
      border-top: 1px solid #21262d;
      vertical-align: middle;
    }}
    tr:hover td {{ background: #1c2128; }}
    .mono {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.8rem; color: #8b949e; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 500;
    }}
    .badge-action  {{ background: #1f3b2e; color: #3fb950; }}
    .badge-convo   {{ background: #1a2d4a; color: #58a6ff; }}
    .badge-both    {{ background: #3b2a4a; color: #bc8cff; }}
    .footer {{
      margin-top: 1.5rem;
      color: #8b949e;
      font-size: 0.75rem;
    }}
  </style>
</head>
<body>
  <h1>Bench Dashboard</h1>
  <p class="subtitle">Bench index — all tracked actions and convos</p>
  <table>
    <thead>
      <tr>
        <th>Slug</th>
        <th>Type</th>
        <th>Convo</th>
        <th>Action</th>
        <th>Jira</th>
        <th>Asana</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>
  <p class="footer">Source: bench-index.csv &nbsp;·&nbsp; Reload page to refresh</p>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request logs

    def do_GET(self):
        keys = load_keys()
        rows = load_index()
        jira_url = keys.get("JIRA_URL", "")
        html = build_html(rows, jira_url)
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"Bench dashboard running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
