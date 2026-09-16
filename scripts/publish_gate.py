#!/usr/bin/env python3
"""publish_gate.py — scan a tree (and optionally a git commit range) for things that must not go public.

    python3 publish_gate.py <dir> [--config gate.json] [--allow 'GLOB::REGEX' ...] [--allow-file F]
                                   [--git-range RANGE] [--json OUT] [--note-scripts]
    python3 publish_gate.py --init-config <path>      # write a config template (keep it OUTSIDE any repo)
    python3 publish_gate.py --selftest

Exit: 0 green (no RED; NOTE may exist) · 1 RED · 2 selftest failed / usage error. The selftest runs first,
shares scan_tree / scan_git_range with the real run, and aborts everything if it fails (fail-loud).

Built-in RED rules (no config needed):
  R04 home-directory and mount paths (macOS and Linux home dirs, private tmp, mounted volumes, a home Desktop)   R05 Windows user paths
  R07 secret shapes (Anthropic/OpenAI/GitHub/AWS/Slack/Google keys, PEM headers)   R08 key/token/secret/password = <long value with digits> (placeholders excluded)
  R09 phone numbers outside the officially fictional ranges (NA 555-01xx, UK 07700 900xxx / 020 7946 0xxx)
  R10 e-mail addresses that are not example/invalid/noreply                         R12 cache dirs, .env, .DS_Store, *.pyc, *.log …
  R15 file >= 100 MB (GitHub rejects)                                                R17 (--git-range) author/committer not in allowed_author_emails
Config rules (your own identifiers, from --config or $PUBLISH_GATE_CONFIG or ~/.config/publish-gate/gate.json):
  U01 identifiers (handles, private mailbox names)  U02 legal names  U03 personal URLs  U04 usernames/hostnames  U05 private project names
NOTE (listed, never red): R13 AI tool names inside archives/binaries · R14 non-Latin scripts (only with --note-scripts) · R15 file >= 50 MB · R16 images (a machine cannot read a screenshot: look at them)
Archives (PK header: zip/xlsx/docx/pptx/jar) are opened up to 3 levels, member names included; PDF Flate streams are inflated and
scanned as text; binaries are scanned as bytes; every file is looked at regardless of extension; anything unreadable is listed as UNSCANNED.
--git-range: every commit in the range (e.g. origin/main..HEAD, or HEAD for all history) has its author/committer, message, and every
added/modified blob scanned with the same rules. Publishing a repo publishes its whole history.
allow entries: GLOB::REGEX — a hit whose relative path matches GLOB and whose line matches REGEX is downgraded to ALLOWED (still printed).
"""
import argparse, datetime, fnmatch, io, json, os, re, subprocess, sys, tempfile, zipfile, zlib

SKIP_DIRS = {".git"}
JUNK_DIRS = {"__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache",
             ".ipynb_checkpoints", ".ruff_cache", ".cache", ".idea", ".vscode"}
JUNK_FILES = re.compile(r"(\.pyc|\.pyo|\.orig|\.rej|\.swp|\.swo|\.log)$|^\.DS_Store$|^Thumbs\.db$|^settings\.local\.json$|^\.env(\.(local|production|development|prod|dev))?$")
MAX_DEPTH, MAX_MEMBER, BIG_NOTE, BIG_RED = 3, 50 << 20, 50 << 20, 100 << 20
IMAGE_EXT = re.compile(r"\.(png|jpe?g|gif|webp|svg|bmp|tiff?|ico)$", re.I)
BUILTIN_RED = [
    # written with \x2f for "/" so that the gate does not flag its own source when it scans itself
    ("R04", "local absolute path", r"\x2fUsers\x2f|\x2fhome\x2f[a-z]|\x2fprivate\x2ftmp\x2f|\x2fVolumes\x2f|~\x2fDesktop|~\x2fDocuments", 0),
    ("R05", "Windows user path", r"\b[A-Za-z]:[\\/]+Users[\\/]", re.I),
    ("R07", "secret shape", r"sk-ant-[A-Za-z0-9_-]{8,}|\bsk-(?:proj-)?[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
                            r"|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}"
                            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----", 0),
]
MASK_RULES = {"R07", "R08"}
ASSIGNED = re.compile(r"\b(api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})", re.I)
PLACEHOLDER = re.compile(r"your|example|placeholder|xxx|change|replace|dummy|sample|test|redacted|insert", re.I)
PHONES = [re.compile(r"\+\d[\d\s().-]{8,}\d"), re.compile(r"(?<![\w.+])\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\w.])")]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
EXAMPLE_MAIL = re.compile(r"@(?:[\w.-]*example[\w.-]*\.(?:com|org|net)|[\w.-]+\.(?:test|invalid|example|localhost)"
                          r"|users\.noreply\.github\.com)$|^noreply@", re.I)
TOOL_RESIDUE = re.compile(r"\b(ChatGPT|OpenAI|Codex|Claude|Anthropic|Copilot|Gemini)\b", re.I)
NONLATIN = re.compile(r"[\u0400-\u04ff\u0590-\u06ff\u0900-\u097f\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
CONFIG_TEMPLATE = {"identifiers": [], "legal_names": [], "urls": [], "usernames": [], "private_names": [],
                   "allowed_author_emails": [], "extra_local_paths": []}
CONFIG_RULES = [("identifiers", "U01", "personal identifier", False), ("legal_names", "U02", "legal name", True),
                ("urls", "U03", "personal URL", False), ("usernames", "U04", "username/hostname", True),
                ("private_names", "U05", "private project name", False)]


def _is_test_number(digits):
    return bool(re.fullmatch(r"1?\d{3}55501\d{2}", digits) or re.fullmatch(r"(?:44|0)7700900\d{3}", digits)
                or re.fullmatch(r"(?:44|0)2079460\d{3}", digits))


def load_config(path):
    if not path:
        for cand in (os.environ.get("PUBLISH_GATE_CONFIG"), os.path.expanduser("~/.config/publish-gate/gate.json")):
            if cand and os.path.isfile(cand):
                path = cand; break
    cfg = dict(CONFIG_TEMPLATE)
    if path:
        cfg.update(json.load(open(path, encoding="utf-8")))
    return cfg, path


class Rules:
    def __init__(self, cfg, note_scripts=False):
        red = list(BUILTIN_RED)
        if cfg.get("extra_local_paths"):
            red[0] = ("R04", "local absolute path", red[0][2] + "|" + "|".join(re.escape(p) for p in cfg["extra_local_paths"]), 0)
        for key, rid, label, word in CONFIG_RULES:
            vals = [v for v in cfg.get(key, []) if v]
            if vals:
                rx = "|".join((r"\b" + re.escape(v) + r"\b") if word else re.escape(v) for v in vals)
                red.append((rid, label, rx, re.I))
        self.text = [(rid, label, re.compile(rx, fl)) for rid, label, rx, fl in red]
        self.bytes = [(rid, label, re.compile(rx.encode("utf-8"), fl)) for rid, label, rx, fl in red]
        self.tool_b = re.compile(TOOL_RESIDUE.pattern.encode("utf-8"), re.I)
        self.authors = set(cfg.get("allowed_author_emails", []))
        self.note_scripts = note_scripts


class Result:
    def __init__(self, allow):
        self.allow = allow
        self.red, self.allowed, self.note, self.unscanned = [], [], [], []
        self.n_files = self.n_text = self.n_bytes = self.n_members = self.n_pdf = 0

    def hit(self, rule, label, where, line_no, line_text, matched, tier="RED"):
        """An allow entry downgrades a hit only when its regex matches within ±24 characters of the match itself —
        never the whole line, so a line that mixes an allowed word with a secret keeps the secret RED."""
        shown = matched[:6] + "…" + f"({len(matched)} chars)" if rule in MASK_RULES else matched
        excerpt = line_text.strip()
        if len(excerpt) > 160:
            i = max(0, excerpt.find(matched[:20]) - 60); excerpt = "…" + excerpt[i:i + 150] + "…"
        if rule in MASK_RULES and matched in excerpt:
            excerpt = excerpt.replace(matched, shown)
        rec = {"rule": rule, "label": label, "where": where, "line": line_no, "match": shown, "excerpt": excerpt}
        if tier == "NOTE":
            self.note.append(rec); return
        base = where.split("::")[0].replace(" (file name)", "")
        pos = line_text.find(matched) if matched else -1
        window = line_text[max(0, pos - 24):pos + len(matched) + 24] if pos >= 0 else ""
        for glob, rx in self.allow:
            if fnmatch.fnmatch(base, glob) and window and rx.search(window):
                rec["allowed_by"] = f"{glob}::{rx.pattern}"; self.allowed.append(rec); return
        self.red.append(rec)


def scan_text(rules, res, where, text, inside):
    lines = text.splitlines() or [""]
    for i, line in enumerate(lines, 1):
        for rid, label, rx in rules.text:
            m = rx.search(line)
            if m:
                res.hit(rid, label, where, i, line, m.group(0))
        for m in ASSIGNED.finditer(line):
            val = m.group(2)
            if sum(c.isdigit() for c in val) >= 3 and not PLACEHOLDER.search(val):
                res.hit("R08", "assigned secret", where, i, line, val)
        for rx in PHONES:
            for m in rx.finditer(line):
                if m.group(0).isdigit():
                    continue
                if not _is_test_number(re.sub(r"\D", "", m.group(0))):
                    res.hit("R09", "non-fictional phone number", where, i, line, m.group(0))
        for m in EMAIL.finditer(line):
            if not EXAMPLE_MAIL.search(m.group(0)):
                local, _, domain = m.group(0).partition("@")
                res.hit("R10", "non-example e-mail", where, i, line, local[:1] + "***@" + domain)
        if inside:
            m = TOOL_RESIDUE.search(line)
            if m:
                res.hit("R13", "AI tool name inside archive/binary", where, i, line, m.group(0), tier="NOTE")
    if not inside and rules.note_scripts and NONLATIN.search(text):
        n = sum(1 for l in lines if NONLATIN.search(l))
        res.hit("R14", "non-Latin script", where, 0, f"{n} lines", f"{n} lines", tier="NOTE")


def scan_bytes(rules, res, where, data):
    for rid, label, rx in rules.bytes:
        m = rx.search(data)
        if m:
            s = m.group(0)[:200].decode("utf-8", "replace"); res.hit(rid, label + " (binary)", where, 0, s, s)
    m = rules.tool_b.search(data)
    if m:
        s = m.group(0).decode("utf-8", "replace"); res.hit("R13", "AI tool name (binary)", where, 0, s, s, tier="NOTE")


def _pdf_streams(data):
    for i, m in enumerate(re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S), 1):
        try:
            yield i, zlib.decompress(m.group(1)).decode("utf-8", "replace")
        except (zlib.error, ValueError):
            continue


def _walk(name, data, depth):
    z = None
    if data[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except (zipfile.BadZipFile, OSError, EOFError):
            z = None
    if z is not None:
        if depth >= MAX_DEPTH:
            yield (name or "file") + f" (archive nested deeper than {MAX_DEPTH}, not opened)", None, "skip"; return
        members = []
        with z:
            try:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    inner = f"{name}::{info.filename}" if name else info.filename
                    members.append((inner, None if info.file_size > MAX_MEMBER else z.read(info), info.filename))
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError) as e:
                yield (name or "file") + f" (archive member unreadable: {type(e).__name__})", None, "skip"
        for inner, blob, member_name in members:
            yield inner + " (member name)", member_name, "text"
            if blob is None:
                yield inner + f" (over {MAX_MEMBER >> 20} MB, not opened)", None, "skip"
            else:
                yield from _walk(inner, blob, depth + 1)
        return
    if data[:5] == b"%PDF-":
        yield name, data, "bytes"
        for i, txt in _pdf_streams(data):
            yield f"{name}::pdf-stream#{i}" if name else f"pdf-stream#{i}", txt, "pdftext"
        return
    if b"\x00" in data[:65536]:
        yield name, data, "bytes"; return
    yield name, data.decode("utf-8", "replace"), "text"


def scan_blob(rules, res, rel, data):
    for member, payload, kind in _walk("", data, 0):
        where = f"{rel}::{member}" if member else rel
        if kind == "skip":
            res.unscanned.append(where)
        elif kind == "bytes":
            res.n_bytes += 1; scan_bytes(rules, res, where, payload)
        elif kind == "pdftext":
            res.n_pdf += 1; scan_text(rules, res, where, payload, inside=True)
        else:
            if member.endswith(" (member name)"):
                res.n_members += 1
            else:
                res.n_text += 1
            scan_text(rules, res, where, payload, inside=bool(member))


def scan_tree(rules, root, allow, big_note=BIG_NOTE, big_red=BIG_RED):
    res, root = Result(allow), os.path.abspath(root)
    for dp, dns, fns in os.walk(root):
        for d in list(dns):
            if d in JUNK_DIRS:
                res.hit("R12", "cache/env directory", os.path.relpath(os.path.join(dp, d), root) + "/", 0, d, d)
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for f in sorted(fns):
            p, rel = os.path.join(dp, f), os.path.relpath(os.path.join(dp, f), root)
            res.n_files += 1
            if JUNK_FILES.search(f):
                res.hit("R12", "junk file on the publish surface", rel, 0, f, f)
            scan_text(rules, res, rel + " (file name)", rel, inside=False)
            try:
                size = os.path.getsize(p)
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError as e:
                res.unscanned.append(f"{rel} (unreadable: {type(e).__name__})"); continue
            if size >= big_red:
                res.hit("R15", "file >= 100 MB (GitHub rejects)", rel, 0, f"{size} bytes", f"{size >> 20} MB")
            elif size >= big_note:
                res.hit("R15", "file >= 50 MB", rel, 0, f"{size} bytes", f"{size >> 20} MB", tier="NOTE")
            if IMAGE_EXT.search(f):
                res.hit("R16", "image (look at it yourself)", rel, 0, f"{size} bytes", f"{size >> 10} KB", tier="NOTE")
            scan_blob(rules, res, rel, data)
    return res


def _git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def scan_git_range(rules, repo, rng, res):
    shas, n_blobs = _git(repo, "log", "--format=%H", rng).split(), 0
    for sha in shas:
        an, ae, cn, ce = _git(repo, "log", "-1", "--format=%an%n%ae%n%cn%n%ce", sha).split("\n")[:4]
        for who, name, mail in (("author", an, ae), ("committer", cn, ce)):
            if rules.authors and mail not in rules.authors:
                res.hit("R17", f"{who} e-mail not in allowed_author_emails", f"commit {sha[:7]}", 0, f"{who}: {mail}", mail)
            scan_text(rules, res, f"commit {sha[:7]} ({who})", f"{name} <{mail}>", inside=False)
        scan_text(rules, res, f"commit {sha[:7]} (message)", _git(repo, "log", "-1", "--format=%B", sha), inside=False)
        raw = _git(repo, "diff-tree", "--root", "-r", "-m", "--no-commit-id", "--raw", "--diff-filter=AM", sha)
        for line in raw.splitlines():
            if not line.startswith(":"):
                continue
            meta, _, path = line.partition("\t")
            n_blobs += 1
            scan_text(rules, res, f"{sha[:7]}:{path} (file name)", path, inside=False)
            scan_blob(rules, res, f"{sha[:7]}:{path}", _git(repo, "cat-file", "blob", meta.split()[3], binary=True))
    return len(shas), n_blobs


def parse_allow(items, path):
    out, raw = [], list(items or [])
    if path:
        raw += [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    for it in raw:
        glob, _, rx = it.partition("::")
        if not rx:
            raise ValueError(f"allow entry needs GLOB::REGEX: {it}")
        out.append((glob, re.compile(rx)))
    return out


# ───────────── selftest: same functions as the real run; one sample per rule; a clean control ─────────────
FAKE_CFG = {"identifiers": ["janedoe1987"], "legal_names": ["Jane Doe"], "urls": ["linkedin.com" "/in/janed"],
            "usernames": ["jdoe-mbp"], "private_names": ["project-nightjar"],
            "allowed_author_emails": ["12345+janed@users.noreply.github.com"], "extra_local_paths": ["/Vol" "umes/Work"]}
SAMPLES = [  # (relative path, bytes, must hit, must not hit) — fragments joined at runtime, see note above
    ("u01.txt", b"reach janedoe1987 on the forum", {"U01"}, set()),
    ("u02.txt", b"Author: Jane Doe", {"U02"}, set()),
    ("u02ok.txt", b"Author: Janet Doeson", set(), {"U02"}),
    ("u03.txt", b"see https://www.linkedin.com" b"/in/janed", {"U03"}, set()),
    ("u04.txt", b"host jdoe-mbp.local", {"U04"}, set()),
    ("u05.txt", b"synced from project-nightjar", {"U05"}, set()),
    ("r04.txt", b"path \x2fUsers\x2fsomeone/Desktop/x.py", {"R04"}, set()),
    ("r04b.txt", b"mounted at \x2fVolumes\x2fWork/data", {"R04"}, set()),
    ("r05.txt", b"C:\x5cUsers\x5csomeone\x5cproj", {"R05"}, set()),
    ("r07.txt", b"key sk-ant-" b"api03-abcdefghijklmnop", {"R07"}, set()),
    ("r08.txt", b'API_KEY = "a1b2c3d4e5f6' b'g7h8i9j0k1l2"', {"R08"}, set()),
    ("r08ok.txt", b'API_KEY = "YOUR_API_KEY_GOES_HERE_12345"\ntoken = localStorage.getItem', set(), {"R08"}),
    ("r09.txt", b"call +1 6" b"04 123 4567", {"R09"}, set()),
    ("r09b.txt", b"call 604-1" b"23-4567 now", {"R09"}, set()),
    ("r09ok.txt", b"+1 202 555 0101 / 604-555-0199 / 020 7946 0123 / 07700 900123 / (202) 555-0199", set(), {"R09"}),
    ("r09c.txt", b"id 2147483648 view/9876543210 ts 1694745600", set(), {"R09"}),
    ("r10.txt", b"mail bob@" b"realcompany.co", {"R10"}, set()),
    ("r10ok.txt", b"a@example.com b@adapter.invalid 12345+janed@users.noreply.github.com noreply@anthropic.com", set(), {"R10"}),
    ("__pycache__/x.pyc", b"\x00cache", {"R12"}, set()),
    (".DS_Store", b"\x00\x00", {"R12"}, set()),
    (".env", b"X=1", {"R12"}, set()),
    (".env.example", b"X=", set(), {"R12"}),
    ("bin.dat", b"\x00\x01\x2fUsers\x2fsomeone/secret\x00", {"R04"}, set()),
    ("clean.md", b"# Clean\nContact a@example.com or +1 202 555 0101. Built with Claude.\n", set(),
     {"R04", "R05", "R07", "R08", "R09", "R10", "R12", "U01", "U02", "U03", "U04", "U05"}),
]


def _make_zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, b in members:
            z.writestr(n, b)
    return buf.getvalue()


def selftest():
    lines, ok = [], True

    def check(cond, label):
        nonlocal ok
        ok &= bool(cond); lines.append(f"  {'✔' if cond else '✘'} {label}")

    rules = Rules(FAKE_CFG)
    with tempfile.TemporaryDirectory() as d:
        for rel, data, _, _ in SAMPLES:
            p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data)
        inner = _make_zip([("theme.xml", b"<a>made with ChatGPT</a>"), ("path.txt", b"\x2fUsers\x2fsomeone/x")])
        open(os.path.join(d, "book.xlsx"), "wb").write(_make_zip([("docProps/app.xml", b"<x>ok</x>"), ("nested.zip", inner), ("names/Jane Doe.txt", b"x")]))
        body = b"BT (\x2fUsers\x2fsomeone/hidden) Tj ET"
        open(os.path.join(d, "doc.pdf"), "wb").write(b"%PDF-1.4\nstream\n" + zlib.compress(body) + b"\nendstream\n%%EOF")
        open(os.path.join(d, "shot.png"), "wb").write(b"\x89PNG\r\n\x1a\n\x00")
        open(os.path.join(d, "big.bin"), "wb").write(b"\x00" * 8)
        res = scan_tree(rules, d, [], big_note=4, big_red=1 << 40)
        by_where = {}
        for rec in res.red:
            by_where.setdefault(rec["where"].split(" (")[0].split("::")[0], set()).add(rec["rule"])
        for rel, _, must, must_not in SAMPLES:
            got = by_where.get(rel, set())
            for r in must:
                check(r in got, f"{rel} hits {r} (got {sorted(got)})")
            for r in must_not:
                check(r not in got, f"{rel} does not hit {r} (got {sorted(got)})")
        check("R12" in by_where.get("__pycache__/", set()), "__pycache__/ directory itself is R12")
        xl = {rec["rule"] for rec in res.red if rec["where"].startswith("book.xlsx")}
        check("R04" in xl, f"path inside a zip nested in an xlsx is R04 (got {sorted(xl)})")
        check("U02" in xl, f"legal name in an archive member name is U02 (got {sorted(xl)})")
        check(any(n["rule"] == "R13" and n["where"].startswith("book.xlsx") for n in res.note), "AI tool name inside the nested zip is a NOTE")
        check("R04" in {rec["rule"] for rec in res.red if rec["where"].startswith("doc.pdf")}, "path inside an inflated PDF stream is R04")
        check(any(n["rule"] == "R16" for n in res.note), "image goes to the NOTE list")
        check(any(n["rule"] == "R15" for n in res.note), "big-file threshold (lowered to 4 bytes) goes to NOTE")
        res2 = scan_tree(rules, d, parse_allow(["u01.txt::janedoe1987"], None))
        check(not any(r["where"].startswith("u01.txt") for r in res2.red) and any(a["where"].startswith("u01.txt") for a in res2.allowed),
              "an allow entry moves u01 from RED to ALLOWED (still listed)")
        open(os.path.join(d, "mixed.txt"), "wb").write(b"contact janedoe1987 " + b"." * 40 + b" key sk-ant-" + b"api03-zzzzzzzzzzzzzzzz")
        res4 = scan_tree(rules, d, parse_allow(["mixed.txt::janedoe1987"], None))
        mixed_red = {r["rule"] for r in res4.red if r["where"].startswith("mixed.txt")}
        mixed_ok = {r["rule"] for r in res4.allowed if r["where"].startswith("mixed.txt")}
        check(mixed_ok == {"U01"} and "R07" in mixed_red, f"allow is per hit, not per line: U01 allowed, the secret on the same line stays RED (red {sorted(mixed_red)}, allowed {sorted(mixed_ok)})")
        rules_ns = Rules(FAKE_CFG, note_scripts=True)
        open(os.path.join(d, "ru.md"), "wb").write("привет".encode("utf-8"))
        res3 = scan_tree(rules_ns, d, [])
        check(any(n["rule"] == "R14" for n in res3.note) and not any(r["rule"] == "R14" for r in res3.red), "--note-scripts: non-Latin text is NOTE, never RED")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "ok.md"), "w").write("# fine\n")
        res = scan_tree(rules, d, [])
        check(not res.red and res.n_files == 1, f"clean directory: 0 RED ({res.n_files} file scanned)")
    with tempfile.TemporaryDirectory() as d:
        def g(*a, env=None):
            e = dict(os.environ, GIT_AUTHOR_NAME="j", GIT_AUTHOR_EMAIL="12345+janed@users.noreply.github.com",
                     GIT_COMMITTER_NAME="j", GIT_COMMITTER_EMAIL="12345+janed@users.noreply.github.com")
            e.update(env or {})
            subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, env=e)
        g("init", "-q"); open(os.path.join(d, "k.txt"), "w").write("token = 'ghp_abcdefghij" "klmnopqrstuvwxyz1234'\n")
        g("add", "k.txt"); g("commit", "-q", "-m", "add key")
        os.remove(os.path.join(d, "k.txt")); g("rm", "-q", "k.txt"); g("commit", "-q", "-m", "remove key")
        open(os.path.join(d, "n.txt"), "w").write("clean\n"); g("add", "n.txt")
        g("commit", "-q", "-m", "note", env={"GIT_AUTHOR_EMAIL": "jane@" "gmail.com"})
        res = Result([]); n_c, n_b = scan_git_range(rules, d, "HEAD", res)
        rules_hits = {r["rule"] for r in res.red}
        check(n_c == 3 and n_b == 2, f"range covered 3 commits / 2 blobs (got {n_c}/{n_b})")
        check("R07" in rules_hits, f"a deleted secret is still found in history → R07 (got {sorted(rules_hits)})")
        check("R17" in rules_hits and "R10" in rules_hits, "a gmail author → R17 + R10")
        check(not scan_tree(rules, d, []).red, "the working tree itself (key deleted) is 0 RED")
    return ok, lines


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("dir", nargs="?"); ap.add_argument("--config"); ap.add_argument("--allow", action="append")
    ap.add_argument("--allow-file"); ap.add_argument("--git-range"); ap.add_argument("--json")
    ap.add_argument("--note-scripts", action="store_true"); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--init-config"); ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    if a.help:
        print(__doc__); return 2
    if a.init_config:
        if os.path.exists(a.init_config):
            print(f"refusing to overwrite {a.init_config}"); return 2
        os.makedirs(os.path.dirname(os.path.abspath(a.init_config)), exist_ok=True)
        json.dump(CONFIG_TEMPLATE, open(a.init_config, "w"), indent=2); print(f"template written: {a.init_config} — fill it, keep it outside every repo"); return 0
    ok, lines = selftest()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"publish_gate selftest · {stamp} · {sum(l.startswith('  ✔') for l in lines)}/{len(lines)} passed")
    if not ok or a.selftest:
        print("\n".join(lines))
        if not ok:
            print("✘ selftest failed — nothing below would be trustworthy; aborting"); return 2
        return 0
    if not a.dir:
        print(__doc__); return 2
    cfg, cfg_path = load_config(a.config)
    rules = Rules(cfg, a.note_scripts)
    try:
        allow = parse_allow(a.allow, a.allow_file)
    except ValueError as e:
        print(e); return 2
    res = scan_tree(rules, a.dir, allow)
    print(f"config: {cfg_path or 'none (built-in rules only — your own identifiers are NOT being checked)'}")
    if a.git_range:
        n_c, n_b = scan_git_range(rules, a.dir, a.git_range, res)
        print(f"git range {a.git_range}: {n_c} commits, {n_b} blobs scanned")
    print(f"scanned {a.dir}: {res.n_files} files · {res.n_text} text · {res.n_bytes} binary · {res.n_members} archive member names · {res.n_pdf} PDF streams")
    for title, rows in (("RED", res.red), ("ALLOWED", res.allowed), ("NOTE", res.note)):
        print(f"{title} ({len(rows)}):")
        for r in rows:
            print(f"  [{r['rule']} {r['label']}] {r['where']}:{r['line']}  {r['match']}   | {r['excerpt'][:120]}" + (f"   allowed by {r['allowed_by']}" if 'allowed_by' in r else ""))
    print(f"UNSCANNED ({len(res.unscanned)}):" + ("" if res.unscanned else " none"))
    for u in res.unscanned:
        print(f"  {u}")
    verdict = "RED" if res.red else "GREEN"
    print(f"verdict: {'🔴 RED — do not publish' if res.red else '🟢 GREEN — NOTE items still need a human look'}")
    if a.json:
        json.dump({"stamp": stamp, "dir": os.path.abspath(a.dir), "config": cfg_path, "git_range": a.git_range, "red": res.red,
                   "allowed": res.allowed, "note": res.note, "unscanned": res.unscanned, "verdict": verdict}, open(a.json, "w"), indent=1, ensure_ascii=False)
    return 1 if res.red else 0


if __name__ == "__main__":
    sys.exit(main())
