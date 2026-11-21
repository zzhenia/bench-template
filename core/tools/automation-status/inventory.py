#!/usr/bin/env python3
"""Write AUTOMATIONS.md at the bench root: every scheduled job this bench runs, with
whether it calls a model, whether it posts to Slack, and what it cost in the last 7 days
(measured from a bench_ai usage ledger when one is configured; OpenClaw agent crons from
their last runs' token counters priced at the active AI profile's model, cache discounts
ignored).

Where jobs are found:
  - Mac launchd: every ~/Library/LaunchAgents plist whose label starts with
    com.bench.<BENCH_SLUG>. or a prefix in config `launchd_prefixes`, or whose
    program/working directory is inside this bench.
  - core/tools/*/schedule.plist templates with no installed plist: listed as "not installed".
  - config `remotes`: other machines over SSH (kind "openclaw" = crontab, OpenClaw crons
    and user services; kind "launchd" = launchctl list + crontab).
Descriptions, ledger operations and Slack flags per job come from config `jobs`.
All of it is optional: config/automation-status.json (see instructions.md).

Run by /status. Standard library only.
"""
import datetime as dt
import json
import os
import plistlib
import re
import sqlite3
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('BENCH_ROOT') or HERE.parents[2])
OUT = ROOT / 'AUTOMATIONS.md'
CONFIG = ROOT / 'config' / 'automation-status.json'
WEEK = 7 * 86400
# USD per million tokens, input / output (list prices). config `prices` adds or overrides.
PRICES = {'claude-haiku-4-5': (1, 5), 'claude-sonnet-5': (3, 15), 'claude-opus-5': (15, 75),
          'claude-fable-5': (10, 50), 'deepseek-flash': (0.30, 1.20), 'deepseek-v4-pro': (1.32, 3.96)}
MODEL_RE = re.compile(r'claude_client|bench_ai|claude -p|anthropic\.|from bench_ai|bench_router')
SLACK_RE = re.compile(r'slack\.com/api|SLACK_BOT_TOKEN|SLACK_USER_TOKEN|chat\.postMessage|openclaw message|slack_dm|notify\(')
TOOL_RE = re.compile(r'((?:core/tools|tools/[^/ ]+)/[^/ ]+)')


def bench_env():
    out = {}
    p = ROOT / 'config' / 'bench.env'
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                out[k.strip()] = v.strip()
    return out


def load_config():
    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    cfg.setdefault('jobs', {})
    cfg.setdefault('launchd_prefixes', [])
    cfg.setdefault('remotes', [])
    slug = bench_env().get('BENCH_SLUG', '').strip()
    cfg['bench_prefix'] = 'com.bench.%s.' % slug if slug else ''
    return cfg


def job(cfg, name):
    j = cfg['jobs'].get(name) or {}
    return j.get('desc', ''), j.get('ledger_op'), j.get('ledger_host'), bool(j.get('slack'))


def sh(cmd, timeout=90):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def marks(paths):
    model = slack = False
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        files = [p] if p.is_file() else [f for f in p.rglob('*') if f.suffix in ('.py', '.sh') and 'venv' not in f.parts and '_old' not in f.name]
        for f in files:
            try:
                t = f.read_text(errors='replace')
            except OSError:
                continue
            model = model or bool(MODEL_RE.search(t))
            slack = slack or bool(SLACK_RE.search(t))
    return model, slack


def ledger(path, since):
    """{operation: (calls, usd)} over the window from a bench_ai usage ledger."""
    out = {}
    if not path or not Path(path).expanduser().exists():
        return out
    try:
        c = sqlite3.connect('file:%s?mode=ro' % Path(path).expanduser(), uri=True)
        for op, n, usd in c.execute("select operation,count(*),coalesce(sum(usd),0) from calls where at>=? and status in ('ok','reserved') group by 1", (since,)):
            out[op] = (n // 2 if n > 1 else n, round(usd, 3))  # ok + reserved rows per call
    except sqlite3.Error:
        pass
    return out


def profile():
    """(active profile name, agent -> model name) from config/ai-profile.json, if the bench has one."""
    p = ROOT / 'config' / 'ai-profile.json'
    try:
        d = json.loads(p.read_text())
        a = d['profiles'][d['active']]['agents']
    except (OSError, ValueError, KeyError):
        return '', lambda agent: ''

    def model_of(agent):
        ref = (a.get('exceptions', {}).get(agent, {}) or {}).get('primary') or a.get('gateway', '')
        return ref.split('/', 1)[-1]
    return d['active'], model_of


def measured(usage, op):
    if not op or op not in usage:
        return 'model, nothing in 7 days'
    n, usd = usage[op]
    return '$%.2f / 7 days (%d calls)' % (usd, n)


def job_name(cfg, label):
    for pre in [cfg['bench_prefix']] + cfg['launchd_prefixes']:
        if pre and label.startswith(pre):
            return label[len(pre):]
    parts = label.split('.')
    if label.startswith('com.bench.') and len(parts) > 3:
        return '.'.join(parts[3:])
    return '.'.join(parts[2:]) if len(parts) > 2 else label


def ours(cfg, label, d):
    if any(p and label.startswith(p) for p in [cfg['bench_prefix']] + cfg['launchd_prefixes']):
        return True
    paths = list(d.get('ProgramArguments', [])) + [d.get('WorkingDirectory', '')]
    return any(str(ROOT) in x for x in paths if x)


def when_launchd(d):
    s, c = d.get('StartInterval'), d.get('StartCalendarInterval')
    if s:
        return 'every %d min' % (s // 60) if s >= 60 else 'every %ds' % s
    if c:
        cs = c if isinstance(c, list) else [c]
        when = 'at ' + ', '.join('%02d:%02d' % (x.get('Hour', 0), x.get('Minute', 0)) for x in cs)
        if cs[0].get('Day'):
            when += ' on day ' + ','.join(str(x.get('Day')) for x in cs)
        if cs[0].get('Weekday') is not None:
            when += ' weekday ' + ','.join(str(x.get('Weekday')) for x in cs)
        return when
    return 'at login'


def mac_jobs(cfg, since):
    rows, installed = [], set()
    usage = ledger(cfg.get('usage_ledger'), since)
    for plist in sorted((Path.home() / 'Library/LaunchAgents').glob('*.plist')):
        try:
            d = plistlib.load(plist.open('rb'))
        except Exception:
            continue
        label = d.get('Label', plist.stem)
        if not ours(cfg, label, d):
            continue
        name = job_name(cfg, label)
        installed.add(name)
        args = [x for x in d.get('ProgramArguments', []) if '/' in x]
        dirs = sorted({m.group(1) for a in args for m in [TOOL_RE.search(a)] if m})
        model, slack = marks([ROOT / x for x in dirs] or args)
        desc, op, host, slack_cfg = job(cfg, name)
        model = model or op is not None
        cost = '$0' if not model else measured(usage, op) if host == 'mac' else 'model, not measured'
        rows.append(('Mac', name, when_launchd(d), model, slack or slack_cfg, cost, desc))
    for tpl in sorted((ROOT / 'core' / 'tools').glob('*/schedule.plist')):
        name = tpl.parent.name
        if name in installed:
            continue
        rows.append(('Mac', name, 'not installed', False, False, '$0',
                     job(cfg, name)[0] or 'schedule template in core/tools/%s; install with core/bin/install-schedules.sh' % name))
    return rows


def cron_words(expr):
    f = expr.split()
    if len(f) != 5:
        return expr
    m, h, dom, mon, dow = f
    if m.startswith('*/') or '/' in m:
        return 'every %s min' % m.split('/')[1]
    if h.startswith('*/') and m.isdigit():
        return 'every %s h' % h[2:]
    if not m.isdigit():
        return expr
    if h == '*':
        return 'every hour at :' + m.zfill(2)
    hours = ', '.join('%02d:%02d' % (int(x), int(m)) for x in h.split(',') if x.isdigit())
    tail = ''
    if dow != '*':
        tail = ' ' + {'1-5': 'Mon–Fri', '1': 'Mon', '0': 'Sun', '2': 'Tue', '5': 'Fri', '7-59/15': ''}.get(dow, 'dow ' + dow)
    return hours + tail


def ssh(r, script, timeout):
    cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % r.get('connect_timeout', 20)]
    if r.get('key'):
        cmd += ['-i', str(Path(r['key']).expanduser())]
    return sh(cmd + [r['ssh'], script], timeout=timeout)


def openclaw_jobs(cfg, r, since, model_of):
    where = r.get('where', r['ssh'])
    svc_re = r.get('services_regex', r'^(bench|openclaw)[^ ]+\.service')
    script = r'''
export PATH=$HOME/.npm-global/bin:$PATH
echo "===CRON"; crontab -l | grep -v '^#\|^PATH\|^$'
echo "===OC"; openclaw cron list --json --all 2>/dev/null
echo "===SVC"; systemctl --user list-unit-files --state=enabled --no-pager 2>/dev/null | grep -oE '%s'
echo "===LEDGER"; python3 -c "
import sqlite3,json,os
c=sqlite3.connect(os.path.expanduser('~/.openclaw/bench-ai/usage.sqlite3'))
print(json.dumps({op:[n,round(usd,3)] for op,n,usd in c.execute(\"select operation,count(*),coalesce(sum(usd),0) from calls where at>=%s and status in ('ok','reserved') group by 1\")}))" 2>/dev/null
echo "===RUNS"; python3 -c "
import sqlite3,json,glob,os
out={}
for db in glob.glob(os.path.expanduser('~/.openclaw/agents/*/agent/openclaw-agent.sqlite')):
    con=sqlite3.connect('file:'+db+'?mode=ro',uri=True)
    for k,raw in con.execute('select session_key,entry_json from session_nodes'):
        if ':cron:' not in k or ':run:' not in k: continue
        e=json.loads(raw); ts=(e.get('updatedAt') or 0)/1000
        if ts<%s or not e.get('totalTokens'): continue
        job=k.split(':cron:')[1].split(':run:')[0]
        out.setdefault(job,[]).append([e.get('inputTokens') or 0,e.get('outputTokens') or 0])
print(json.dumps(out))" 2>/dev/null
''' % (svc_re, since, since)
    text = ssh(r, script, 120)
    if '===CRON' not in text:
        return [(where, 'unreachable', '', False, False, '', r.get('unreachable_note', 'did not answer'))]
    sect = {}
    for part in text.split('===')[1:]:
        key, _, body = part.partition('\n')
        sect[key.strip()] = body
    try:
        usage = {k: (v[0] // 2 if v[0] > 1 else v[0], v[1]) for k, v in json.loads(sect.get('LEDGER', '{}') or '{}').items()}
    except ValueError:
        usage = {}
    try:
        runs = json.loads(sect.get('RUNS', '{}') or '{}')
    except ValueError:
        runs = {}
    prices = {**PRICES, **{k: tuple(v) for k, v in cfg.get('prices', {}).items()}}
    rows = []
    for line in sect.get('CRON', '').splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        when, cmd = ' '.join(parts[:5]), parts[5]
        key = next((k for k in cfg['jobs'] if k.replace('_', '-') in cmd.replace('_', '-')), None)
        desc, op, host, slack = job(cfg, key)
        model = op is not None
        rows.append((where, key or cmd[:40], cron_words(when), model, slack, '$0' if not model else measured(usage, op), desc))
    try:
        jobs = json.loads(sect.get('OC', '{}') or '{}').get('jobs', [])
    except ValueError:
        jobs = []
    tz = r.get('timezone_label', '')
    for j in jobs:
        if not j.get('enabled', True):
            continue
        name, agent = j['name'], j.get('agentId') or 'main'
        model_name = model_of(agent)
        pin, pout = prices.get(model_name, (0, 0))
        rr = runs.get(j['id'], [])
        if rr:
            per = sum(i * pin + o * pout for i, o in rr) / len(rr) / 1e6
            cost = '≤$%.2f / run (%d runs, %s)' % (per, len(rr), model_name)
        else:
            cost = 'model %s, no run in 7 days' % model_name
        when = cron_words((j.get('schedule') or {}).get('expr', '')) + (' ' + tz if tz else '') + ', agent ' + agent
        rows.append((where, name, when, True, True, cost, job(cfg, name)[0]))
    for svc in sect.get('SVC', '').split():
        key = svc.replace('.service', '')
        desc, op, host, slack = job(cfg, key)
        rows.append((where, key, 'always on', op is not None, slack, measured(usage, op) if op else '$0', desc))
    return rows


def launchd_remote_jobs(cfg, r):
    where = r.get('where', r['ssh'])
    label_re = r.get('label_regex') or cfg['bench_prefix'] or 'com.bench.'
    text = ssh(r, 'launchctl list | grep -E "%s" | awk \'{print $3}\'; crontab -l 2>/dev/null | grep -v "^#"; echo ==ok' % label_re, 20)
    if '==ok' not in text:
        return [(where, 'unreachable', '', False, False, '$0', r.get('unreachable_note', 'did not answer'))]
    text = text.replace('==ok', '')
    if not text.strip():
        return [(where, 'nothing scheduled', '', False, False, '$0', r.get('empty_note', 'no bench jobs, no crontab'))]
    return [(where, line.strip(), 'at login', False, False, '?', 'still installed') for line in text.splitlines() if line.strip()]


def main():
    cfg = load_config()
    since = int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).timestamp())
    active, model_of = profile()
    rows = []
    for r in cfg['remotes']:
        if r.get('kind') == 'openclaw':
            rows += openclaw_jobs(cfg, r, since, model_of)
    rows += mac_jobs(cfg, since)
    for r in cfg['remotes']:
        if r.get('kind') == 'launchd':
            rows += launchd_remote_jobs(cfg, r)
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    intro = ('Every scheduled job on the bench, regenerated by `/status` '
             '(`core/tools/automation-status/inventory.py`). Generated %s' % now)
    if active:
        intro += '; active AI profile `%s`' % active
    intro += ('. Cost = the last 7 days from the usage ledgers; agent crons are the last runs\' tokens at list '
              'prices, cache discounts ignored (an upper bound).')
    lines = ['# Automations', '', intro, '',
             '| # | Where | Job | When | Model | Slack | Cost | What it does |', '|---|---|---|---|---|---|---|---|']
    for i, (where, name, when, model, slack, cost, desc) in enumerate(rows, 1):
        lines.append('| %d | %s | %s | %s | %s | %s | %s | %s |' % (i, where, name, when, 'yes' if model else '–', 'yes' if slack else '–', cost, desc))
    n_model = sum(1 for r in rows if r[3])
    stop = 'a Mac job: `launchctl bootout gui/$(id -u)/<label>` and delete its plist'
    if any(r.get('kind') == 'openclaw' for r in cfg['remotes']):
        stop = 'an OpenClaw cron: `openclaw cron disable <id>` on that host; a cron line: `crontab -e` there; ' + stop
    lines += ['', '%d jobs, %d call a model. To stop one: %s.' % (len(rows), n_model, stop), '']
    OUT.write_text('\n'.join(lines))
    print(OUT)


if __name__ == '__main__':
    main()
