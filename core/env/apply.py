#!/usr/bin/env python3
"""Merge the bench's settings for each environment into this machine's files.

Each folder next to this script (cursor/, warp/, claude/) has an env.json listing
fragments and the file each one merges into. Per setting:
  missing here          -> added
  same value            -> nothing
  different value here  -> the user decides (bench value or theirs), once;
                           the answer is remembered until the bench value changes.
Every changed file is backed up first to <file>_oldNN (next free number).
An environment whose app is not installed (target folder missing) is skipped.

  apply.py                      apply; in a terminal, ask about each conflict
  apply.py --check              change nothing; list what would change
  apply.py --choose ENV:KEY=bench|mine [...]
                                answer conflicts without a prompt (for /update)

Exit 0 = done, nothing open. Exit 2 = conflicts need an answer; each is printed
as `CONFLICT <env>:<key> | here: <value> | bench: <value>`.
"""
import json, os, re, sys, tomllib
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent
BENCH_DIR = ENV_DIR.parent.parent
CHOICES = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "bench" / "env-choices.json"


# ---------- helpers ----------

def subst(text: str) -> str:
    return text.replace("{{BENCH_DIR}}", str(BENCH_DIR)).replace("{{HOME}}", str(Path.home()))


def backup(path: Path) -> Path:
    n = 1
    while (b := path.with_name(f"{path.name}_old{n:02d}")).exists():
        n += 1
    b.write_bytes(path.read_bytes())
    return b


def show(v) -> str:
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    return s if len(s) <= 70 else s[:67] + "..."


# ---------- JSONC, top-level keys (Cursor's settings.json keeps comments) ----------

def jsonc_load(text: str) -> dict:
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1]); i = j + 1
        elif text.startswith("//", i):
            i = text.find("\n", i); i = n if i < 0 else i
        elif text.startswith("/*", i):
            i = text.index("*/", i) + 2
        else:
            out.append(c); i += 1
    s = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    return json.loads(s) if s.strip() else {}


def jsonc_spans(text: str) -> dict:
    """Top-level key -> (value_start, value_end) offsets; also '__close__' -> offset of final '}'
    and '__last__' -> end offset of the last significant char before it."""
    spans, i, n, depth = {}, 0, len(text), 0
    key, vstart, last_sig, expecting_key = None, None, None, False
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            i = text.find("\n", i); i = n if i < 0 else i; continue
        if text.startswith("/*", i):
            i = text.index("*/", i) + 2; continue
        if c.isspace():
            i += 1; continue
        if c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if depth == 1 and expecting_key:
                key = json.loads(text[i:j + 1]); expecting_key = False
            elif depth == 1 and vstart is None and key is not None:
                vstart = i
            last_sig = j + 1; i = j + 1; continue
        if depth == 1 and c == ":" and key is not None and vstart is None:
            i += 1; continue
        if depth == 1 and key is not None and vstart is None and c not in ",}":
            vstart = i
        if c in "{[":
            depth += 1
            if depth == 1:
                expecting_key = True
        elif c in "}]":
            depth -= 1
            if depth == 0:
                if key is not None and vstart is not None:
                    spans[key] = (vstart, last_sig)
                spans["__close__"] = i
                break
        elif c == "," and depth == 1:
            if key is not None and vstart is not None:
                spans[key] = (vstart, last_sig)
            key, vstart, expecting_key = None, None, True
            last_sig = i + 1; i += 1; continue
        last_sig = i + 1
        i += 1
    # last significant char before the closing brace
    k = spans["__close__"] - 1
    body = text[:spans["__close__"]]
    stripped = re.sub(r"//[^\n]*", lambda m: " " * len(m.group()), body)
    while k >= 0 and stripped[k].isspace():
        k -= 1
    spans["__last__"] = k + 1
    return spans


def jsonc_dump(v, indent="    ") -> str:
    return json.dumps(v, indent=4, ensure_ascii=False).replace("\n", "\n" + indent)


class JsoncTop:
    def __init__(self, path: Path):
        self.text = path.read_text() if path.exists() else "{\n}\n"

    def current(self) -> dict:
        return jsonc_load(self.text)

    def set(self, key, value):
        sp = jsonc_spans(self.text)
        if key in sp:
            a, b = sp[key]
            self.text = self.text[:a] + jsonc_dump(value) + self.text[b:]
        else:
            at = sp["__last__"]
            prev = self.text[at - 1] if at else "{"
            sep = "" if prev in "{," else ","
            self.text = (self.text[:at] + sep + f'\n    {json.dumps(key)}: {jsonc_dump(value)}'
                         + self.text[at:])
        jsonc_load(self.text)  # still valid

    def leaves(self, frag: dict) -> dict:
        return {k: v for k, v in frag.items() if not k.startswith("_")}

    def get(self, cur, key):
        return cur.get(key, MISSING)


# ---------- plain JSON, nested keys (Claude Code's settings.json) ----------

MISSING = object()


class JsonDeep:
    def __init__(self, path: Path):
        self.data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}

    def current(self):
        return self.data

    def leaves(self, frag, prefix=""):
        out = {}
        for k, v in frag.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and v:
                out.update(self.leaves(v, f"{prefix}{k}."))
            else:
                out[f"{prefix}{k}"] = v
        return out

    def get(self, cur, key):
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return MISSING
            cur = cur[part]
        return cur

    def set(self, key, value):
        d, parts = self.data, key.split(".")
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = value

    @property
    def text(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"


# ---------- TOML, [table] key = value lines (Warp's settings.toml) ----------

def toml_frag(text: str) -> dict:
    """'table.key' -> raw value text, in fragment order."""
    out, table = {}, ""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("["):
            table = s.strip("[]").strip(); continue
        k, _, v = s.partition("=")
        out[f"{table}\0{k.strip()}"] = v.strip()
    return out


class TomlLines:
    def __init__(self, path: Path):
        self.text = path.read_text() if path.exists() else ""

    def current(self):
        return tomllib.loads(self.text)

    def leaves(self, frag):
        return frag

    def get(self, cur, key):
        table, k = key.split("\0")
        for part in (table.split(".") if table else []) + [k]:
            if not isinstance(cur, dict) or part not in cur:
                return MISSING
            cur = cur[part]
        return cur

    def set(self, key, raw):
        table, k = key.split("\0")
        lines = self.text.splitlines()
        hdr = f"[{table}]"
        start = next((i for i, l in enumerate(lines) if l.strip() == hdr), None) if table else -1
        if start is None:
            lines += ["", hdr, f"{k} = {raw}"]
        else:
            end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("[")), len(lines))
            hit = next((i for i in range(start + 1, end) if re.match(rf"\s*{re.escape(k)}\s*=", lines[i])), None)
            if hit is not None:
                lines[hit] = f"{k} = {raw}"
            else:
                at = end
                while at > start + 1 and not lines[at - 1].strip():
                    at -= 1
                lines.insert(at, f"{k} = {raw}")
        self.text = "\n".join(lines) + "\n"
        tomllib.loads(self.text)  # still valid


# ---------- YAML flat map, one "key": value per line (Warp keybindings) ----------

class YamlFlat:
    LINE = re.compile(r'^\s*("[^"]+"|[^#:\s][^:]*):\s*(.*?)\s*$')

    def __init__(self, path: Path):
        self.text = path.read_text() if path.exists() else "---\n"

    def _map(self, text):
        out = {}
        for l in text.splitlines():
            if l.strip().startswith("#") or l.strip() == "---":
                continue
            m = self.LINE.match(l)
            if m:
                out[m.group(1).strip('"')] = m.group(2)
        return out

    def current(self):
        return self._map(self.text)

    def leaves(self, frag):
        return frag

    def get(self, cur, key):
        return cur.get(key, MISSING)

    def set(self, key, value):
        lines = self.text.splitlines()
        for i, l in enumerate(lines):
            m = self.LINE.match(l)
            if m and not l.strip().startswith("#") and m.group(1).strip('"') == key:
                lines[i] = f'"{key}": {value}'
                break
        else:
            lines.append(f'"{key}": {value}')
        self.text = "\n".join(lines) + "\n"


FORMATS = {"jsonc": JsoncTop, "json": JsonDeep, "toml": TomlLines, "yaml": YamlFlat}


def load_frag(fmt, path: Path):
    text = subst(path.read_text())
    if fmt in ("jsonc", "json"):
        return json.loads(text)
    if fmt == "toml":
        return toml_frag(text)
    return YamlFlat(path)._map(text)


def same(fmt, here, bench):
    if fmt == "toml":
        return here == tomllib.loads(f"v = {bench}")["v"]
    return here == bench


def label(key):
    return key.replace("\0", ".")


# ---------- main ----------

def main(argv):
    check = "--check" in argv
    given = {}
    if "--choose" in argv:
        for a in argv[argv.index("--choose") + 1:]:
            k, _, v = a.rpartition("=")
            given[k] = v
    try:
        remembered = json.loads(CHOICES.read_text())
    except (OSError, ValueError):
        remembered = {}
    interactive = sys.stdin.isatty() and not check
    open_conflicts, report = [], []

    for envfile in sorted(ENV_DIR.glob("*/env.json")):
        env = envfile.parent.name
        for t in json.loads(envfile.read_text())["targets"]:
            target = Path(os.path.expanduser(subst(t["target"])))
            if not target.parent.is_dir():
                report.append(f"{env}: skipped, {target.parent} not found (app not installed)")
                continue
            fmt = t["format"]
            doc = FORMATS[fmt](target)
            cur = doc.current()
            changed = []
            for key, bench in doc.leaves(load_frag(fmt, ENV_DIR / env / t["fragment"])).items():
                here = doc.get(cur, key)
                # An object value (editorAssociations, autoLockGroups) adds the bench's
                # entries to the user's own; only a changed entry is a conflict.
                if isinstance(here, dict) and isinstance(bench, dict):
                    merged = {**here, **bench}
                    if merged == here:
                        continue
                    if all(here.get(k, merged[k]) == merged[k] for k in merged):
                        doc.set(key, merged); changed.append(label(key)); continue
                    bench = merged
                if here is not MISSING and same(fmt, here, bench):
                    continue
                cid = f"{env}:{label(key)}"
                bench_s = bench if isinstance(bench, str) else json.dumps(bench, sort_keys=True)
                if here is MISSING:
                    take = True
                else:
                    ans = given.get(cid)
                    mem = remembered.get(cid)
                    if not ans and mem and mem.get("bench") == bench_s:
                        ans = mem["choice"]
                    if not ans and interactive:
                        print(f"\n{env}: {label(key)}\n  here:  {show(here)}\n  bench: {show(bench)}")
                        while ans not in ("bench", "mine"):
                            r = input("  Use the bench value (b) or keep yours (k)? ").strip().lower()
                            ans = {"b": "bench", "k": "mine"}.get(r[:1])
                    if not ans:
                        open_conflicts.append(f"CONFLICT {cid} | here: {show(here)} | bench: {show(bench)}")
                        continue
                    if not check:
                        remembered[cid] = {"choice": ans, "bench": bench_s}
                    take = ans == "bench"
                if take:
                    doc.set(key, bench)
                    changed.append(label(key))
            if changed:
                if check:
                    report.append(f"{env}: would set {', '.join(changed)} in {target}")
                else:
                    b = backup(target) if target.exists() else None
                    target.write_text(doc.text)
                    report.append(f"{env}: set {', '.join(changed)} in {target}"
                                  + (f" (backup {b.name})" if b else ""))

    if not check and remembered:
        CHOICES.parent.mkdir(parents=True, exist_ok=True)
        CHOICES.write_text(json.dumps(remembered, indent=2) + "\n")
    print("\n".join(report + open_conflicts) or "Environment settings already match.")
    return 2 if open_conflicts else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
