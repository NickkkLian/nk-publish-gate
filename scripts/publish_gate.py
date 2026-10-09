#!/usr/bin/env python3
"""publish_gate.py — scan a tree (and optionally a git commit range) for things that must not go public.

    python3 publish_gate.py <dir> [--config gate.json] [--allow 'RULES::GLOB::REGEX' ...] [--allow-file F]
                                   [--git-range RANGE] [--json OUT] [--note-scripts]
    python3 publish_gate.py --init-config <path>      # write a config template (keep it OUTSIDE any repo)
    python3 publish_gate.py --selftest

Exit: 0 green (no RED; NOTE may exist) · 1 RED · 2 selftest failed / usage error. The selftest runs first,
shares scan_tree / scan_git_range with the real run, and aborts everything if it fails (fail-loud).

Built-in RED rules (no config needed):
  R04 home-directory and mount paths (macOS and Linux home dirs, private tmp, mounted volumes, a home Desktop)   R05 Windows user paths
      (0.1.7: a home path whose whole user folder name is a stand-in, see STANDIN_USERS, is a NOTE; a drive-letter path
      written with forward slashes is reported once, by R05, unless an allow entry covers the R05 finding)
  R07 secret shapes (Anthropic/OpenAI/GitHub/AWS/Slack/Google/Stripe/npm/GitLab/SendGrid/Twilio/Hugging Face keys, JWTs, PEM headers;
      a short list, not a secret scanner: run gitleaks or trufflehog as well)   R08 key/token/secret/password = <long value with digits> (placeholders excluded)
  R09 international/separated, leading-zero national, phone-word bare and Chinese national phone shapes;
      fiction: NA 555-01xx, UK 07700 900xxx / 020 7946 0xxx, exact ACMA mobiles/services and geographical ranges
      (0.1.7: a number written with +1 and area code 555 is a NOTE: that area code is not assignable)
  R10 e-mail addresses that are not example/invalid/noreply (0.1.7: a package name, an @ and a version number are not an
      address; each is a NOTE record, printed as one line per file with the count; an @ followed by four numbers stays
      RED; an address whose two sides are both stand-ins, see STANDIN_MAIL_LOCAL and STANDIN_MAIL_DOMAIN, is a NOTE)                       R12 cache dirs, .env, .DS_Store, *.pyc, *.log …
  R15 file >= 100 MB (GitHub rejects)                                                R17 (--git-range) author/committer not in allowed_author_emails
Config rules (your own identifiers, from --config or $PUBLISH_GATE_CONFIG or ~/.config/publish-gate/gate.json):
  U01 identifiers (handles, private mailbox names)  U02 legal names  U03 personal URLs  U04 usernames/hostnames  U05 private project names
NOTE (listed, never red): R04/R05 home paths with a stand-in user · R09 +1 numbers in area code 555 · R10 name@version counts and stand-in addresses · R13 AI tool names inside archives/binaries · R14 non-Latin scripts (only with --note-scripts) · R15 file >= 50 MB · R16 images (a machine cannot read a screenshot: look at them)
Repeats (0.1.7): the same e-mail address, the same phone digits or the same home-path user folder is printed as one RED line with
its count and its first place; the name@version NOTEs of one file are one line. The exit code, the verdict and --json are not
affected: --json lists every place and every string.
Archives (PK header: zip/xlsx/docx/pptx/jar) are opened up to 3 levels, member names included; PDF Flate streams are inflated and
scanned as text; binaries are scanned as bytes; every file is looked at regardless of extension; anything unreadable is listed as UNSCANNED.
--git-range: every commit in the range (e.g. origin/main..HEAD, or HEAD for all history) has its author/committer, message, and every
added/modified blob scanned with the same rules. Publishing a repo publishes its whole history.
allow entries: RULES::GLOB::REGEX (or GLOB::REGEX). A hit is downgraded to ALLOWED (still printed) only when its rule is in RULES
(a comma list such as R10 or U01,U02; the two-field form takes any rule), its relative path matches GLOB, and a match of REGEX
on the same line covers the matched text itself (in a binary: within 200 bytes on either side). Every match on a line is its own hit.
0.1.2 changed this: until 0.1.1 an entry counted if REGEX matched within 24 characters of a hit, so an allowed word could hide a
secret or a path right next to it; two-field entries are still read, and judged by the new rule.
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
    ("R07", "secret shape", r"sk-ant-[A-Za-z0-9_-]{8,}|\bsk-(?:proj-)?[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}"
                            r"|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}"
                            r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                            # 0.1.3: six more published formats (a review found 4 of 10 common shapes caught). Still a short
                            # list: a dedicated secret scanner (gitleaks, trufflehog) knows hundreds. Run one as well.
                            r"|\b[sr]k_live_[A-Za-z0-9]{16,}"                                   # Stripe live secret / restricted key
                            r"|\bnpm_[A-Za-z0-9]{36}"                                           # npm access token
                            r"|\bglpat-[A-Za-z0-9_-]{20,}"                                      # GitLab personal access token
                            r"|\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}"                      # SendGrid API key
                            r"|\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"  # a signed JSON Web Token
                            r"|\bSK[0-9a-fA-F]{32}\b"                                          # Twilio API key SID
                            r"|\bhf_[A-Za-z0-9]{30,}", 0),                                      # Hugging Face token
]
MASK_RULES = {"R07", "R08"}
ASSIGNED = re.compile(r"\b(api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})", re.I)
PLACEHOLDER = re.compile(r"your|example|placeholder|xxx|change|replace|dummy|sample|test|redacted|insert", re.I)
PHONES = [
    re.compile(r"\+\d[\d\s().-]{8,}\d"),
    re.compile(r"(?<![\w.+])\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\w|\.\d)"),
]
# Leading-zero national forms: retain only 10--12 digits, excluding fiction.
PHONE_NATIONAL0 = re.compile(r"(?<![\w.+])\(?0[1-9]\d{0,3}\)?(?:[\s.-]?\d{3,8}){1,2}(?!\w|\.\d)")
NATIONAL0_DIGITS = (10, 12)
# A bare nonzero 10/11-digit run requires a preceding phone word within 24 characters.
PHONE_BARE_RUN = re.compile(r"(?<![\w.+])[1-9]\d{9,10}(?!\w|\.\d)")
PHONE_WORD = re.compile(r"phone|\btel\b|mobile|\bcell\b|whatsapp|\bfax\b|\bsms\b|电话|手机|致电", re.I)
PHONE_WORD_WINDOW = 24
# Chinese national mobile shape: 11 digits starting 13--19, compact or 3-4-4.
# Unconditional, including matching IDs; no fiction exemption for this shape.
PHONE_CN_MOBILE = re.compile(r"(?<![\w.+])1[3-9]\d(?:[ -]?\d{4}){2}(?!\w|\.\d)")
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

# 0.1.7. A home path is a NOTE, not RED, when its user folder name is, as a whole, one of these words (or three dots,
# or a name in angle brackets). The whole name is judged: it runs to the next path separator, spaces included, so a
# profile folder made of a first name and a surname is never judged by its first word. A single character is not a
# stand-in. This is the whole list, and it is short on purpose; any other name is RED, invented ones such as jane
# included, because the gate cannot tell an invented name from a real one. A real account whose name is exactly one of
# these words is a NOTE too: if that is yours, put it in the config (`usernames`), which is RED wherever it appears.
STANDIN_USERS = {"user", "username", "yourusername", "you", "name", "me", "dev", "node"}
# 0.1.7. An e-mail address is a NOTE only when BOTH sides are stand-ins: the part before the @ is in the first list and
# the domain is in the second. Each list is short on purpose and holds no mail provider and no company that sells
# anything under that name: every other address stays RED.
STANDIN_MAIL_LOCAL = {"user", "test", "name", "you", "your", "your-email", "email", "foo", "bar", "john.doe", "jane.doe",
                      "firstname.lastname", "a", "b"}
STANDIN_MAIL_DOMAIN = {"company.com", "yourcompany.com", "yourdomain.com", "yourapp.com", "acme.com", "contoso.com",
                       "test.com", "tenant.com", "b.com", "bar.com", "attacker.com", "evil.com"}
# 0.1.7. Area code 555 is not assignable (NANPA NPA Database, read 2026-10-08: the row for 555 says ASSIGNABLE No;
# reports.nanpa.com/public/npa_report.csv). A number written with the country code +1 and that area code is therefore
# a NOTE. A NOTE is not proof that the number belongs to nobody. Only that shape: the + and the 1 must be written, and
# the match must be exactly eleven digits. Ten digits starting 555 with no country code stay RED (another country's
# national number can look like that), and so does 555 in the middle (a real area code followed by 555).
AREA_555 = re.compile(r"1555\d{7}")
VALUE_RULES = {"R04", "R05", "R09", "R10"}       # rules whose finding is a value; repeats of one value print as one line
USER_PART = re.compile(r"[\\\x2f]*(<[^<>\\\x2f\n]{0,40}>?|\.{3}|\u2026|[^\\\x2f\s\"'`)(\]\[,;:|&=#]*)")
# the rest of a folder name that has spaces in it: words that run on, with no space before the next path separator
NAME_MORE = re.compile(r"((?:[ \t]+[^\x00-\x20\\\x2f\"'`<>|]+)+)[\\\x2f]")
NAME_TAIL = re.compile(r"[^\x00-\x20\\\x2f\"'`)(\]\[,;:|&=#]*")
ANGLE_NAME = re.compile(r"<[^<>]*>")
MAIL_EDGE = set(" \t<>()[]{}\"'`,;:=|\\\x2f")   # what may stand right before an address that is judged as a stand-in
HOME_LINUX = re.compile(r"\x2fhome\x2f[a-z]")
VERSION_START = re.compile(r"\d")


def _home_user(rid, matched, after):
    """The user part of a home path, as written; None when the match is not a home path at all (a mounted volume, a tmp
    folder, a home Desktop, an entry of extra_local_paths). `after` is the text that follows the match."""
    if rid == "R04":
        if HOME_LINUX.fullmatch(matched):
            after = matched[-1] + after          # the rule's own match already holds the name's first letter
        elif matched != "\x2fUsers\x2f":
            return None
    elif rid != "R05":
        return None
    m = USER_PART.match(after)
    part = m.group(1) + NAME_TAIL.match(after, m.end()).group(0)     # the whole name, to the next separator or the end of the word
    more = NAME_MORE.match(after, m.start(1) + len(part))
    if more:                                     # a folder name with spaces: it is one name, and it is judged whole
        part += more.group(1)
    return part


def _standin_user(rid, matched, after):
    """The user part of a home path when it is a stand-in; None when it is a name, or not a home path."""
    part = _home_user(rid, matched, after)
    if part is None:
        return None
    if part in ("...", "\u2026") or ANGLE_NAME.fullmatch(part):
        return part
    name = part.rstrip(".!?")                    # the full stop of a sentence that ends on the path
    return name if name.lower() in STANDIN_USERS else None


def _standin_shown(matched, standin):
    return (matched[:-1] if HOME_LINUX.fullmatch(matched) else matched) + standin


def _is_version(domain):
    """True when the part after the @ is a version and not a domain: it starts with a number, a dot and a digit, and
    its last part has a digit in it (no top-level domain does). An @ followed by four numbers is an IP address, as in
    a login to a machine, whatever follows the fourth number: it stays an address. Three numbers or fewer cannot be
    told from a version."""
    parts = domain.split(".")
    if len(parts) >= 4 and all(x.isdigit() for x in parts[:3]) and VERSION_START.match(parts[3]):
        return False
    return parts[0].isdigit() and bool(VERSION_START.match(parts[1])) and any(c.isdigit() for c in parts[-1])


def _inside(span, spans):
    return any(a <= span[0] and span[1] <= b for a, b in spans)


def _phone_value(matched):
    """The digits, exactly as written: two numbers are the same value only when every digit is the same."""
    return re.sub(r"\D", "", matched)


def printed(rows):
    """A list as it is printed: [record, count, files] per line. Records that carry the same value under the same rule
    and label are one line (the first place, with the count); every other record is its own line. The value is the
    whole e-mail address, the phone digits or the whole user folder name, each exactly as written; for a name@version
    NOTE it is the file, so one file is one line."""
    out, at = [], {}
    for r in rows:
        key = (r["rule"], r["label"], r.get("_value"))
        if r.get("_value") is not None and key in at:
            at[key][1] += 1; at[key][2].add(r["where"].split("::")[0])
        else:
            out.append([r, 1, {r["where"].split("::")[0]}])
            if r.get("_value") is not None:
                at[key] = out[-1]
    return out


def public(rows):
    """Records as --json writes them: without the grouping value, so the file is the same as before 0.1.7."""
    return [{k: v for k, v in r.items() if k != "_value"} for r in rows]


# ACMA, read 2026-10-07 (page last updated 2026-09-03):
# https://www.acma.gov.au/phone-numbers-use-tv-shows-films-and-creative-works
# Only these exact mobiles/services; geographical ranges are 02/03/07/08 + 5550/7010 + xxxx.
AU_FICTION_MOBILES = frozenset({
    "0491" "570006", "0491" "570156", "0491" "570157", "0491" "570158", "0491" "570159", "0491" "570110",
    "0491" "570313", "0491" "570737", "0491" "571266", "0491" "571491", "0491" "571804", "0491" "572549",
    "0491" "572665", "0491" "572983", "0491" "573770", "0491" "573087", "0491" "574118", "0491" "574632",
    "0491" "575254", "0491" "575789", "0491" "576398", "0491" "576801", "0491" "577426", "0491" "577644",
    "0491" "578957", "0491" "578148", "0491" "578888", "0491" "579212", "0491" "579760", "0491" "579455",
})
AU_FICTION_SERVICES = frozenset({
    "1800" "160401", "1800" "975707", "1800" "975708", "1800" "975709", "1800" "975710", "1800" "975711",
    "1300" "975707", "1300" "975708", "1300" "975709", "1300" "975710", "1300" "975711",
})
AU_FICTION_GEOGRAPHIC = re.compile(r"(?:0|61)[2378](?:5550|7010)\d{4}")
TEST_PHONE_DATE = re.compile(
    r"(?P<phone>[+\d().-]+(?: [+\d().-]+)*)(?P<delimiter>\t+| {2,})"
    r"(?P<date>\d{4}-\d{2}-\d{2})(?: (?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?)?")


def _is_test_number(digits):
    au_national = "0" + digits[2:] if digits.startswith("61") else digits
    au_service = digits[2:] if digits.startswith("61") else digits
    return bool(re.fullmatch(r"1?\d{3}55501\d{2}", digits)
                or re.fullmatch(r"(?:44|0)7700900\d{3}", digits)
                or re.fullmatch(r"(?:44|0)2079460\d{3}", digits)
                or au_national in AU_FICTION_MOBILES
                or AU_FICTION_GEOGRAPHIC.fullmatch(digits)
                or au_service in AU_FICTION_SERVICES)


def _is_test_national0(digits):
    """Fiction ranges for a number written with a leading 0. The North American clause of _is_test_number is left out
    on purpose: no area code there starts with 0, and `\\d{3}55501\\d{2}` would accept real Australian mobiles
    (the leading zero is not a North American area code)."""
    return bool(re.fullmatch(r"0(?:7700900|2079460)\d{3}", digits)
                or digits in AU_FICTION_MOBILES
                or AU_FICTION_GEOGRAPHIC.fullmatch(digits))


def _test_phone_date_span(line, match):
    """One exception: exactly a test number, a column delimiter, and an ISO date/time."""
    candidate = match.group(0)
    # The original regex stops at ':' in a time. Include the remaining suffix only
    # for this check; fullmatch rejects incomplete times or anything after the time.
    if line[match.end():].startswith(":"):
        candidate = line[match.start():]
    dated = TEST_PHONE_DATE.fullmatch(candidate)
    if not dated or not _is_test_number(re.sub(r"\D", "", dated.group("phone"))):
        return None
    try:
        datetime.date.fromisoformat(dated.group("date"))
    except ValueError:
        return None
    return (match.start(), match.end(), match.start() + dated.start("delimiter"),
            match.start() + dated.start("date"))


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
        self.r05 = next(rx for rid, _, rx in self.text if rid == "R05")
        self.r05_b = next(rx for rid, _, rx in self.bytes if rid == "R05")
        self.tool_b = re.compile(TOOL_RESIDUE.pattern.encode("utf-8"), re.I)
        self.authors = set(cfg.get("allowed_author_emails", []))
        self.note_scripts = note_scripts


class Result:
    def __init__(self, allow):
        self.allow = allow
        self.red, self.allowed, self.note, self.unscanned = [], [], [], []
        self.n_files = self.n_text = self.n_bytes = self.n_members = self.n_pdf = 0

    def allowed_by(self, rule, where, text, span):
        """The allow entry that covers this hit, or None. An entry covers a hit only when it names the hit's rule (a
        two-field entry names every rule), its GLOB matches the path, and one match of its REGEX in `text` spans the
        matched text itself — a neighbour on the same line is never enough, however close (0.1.1 accepted anything
        within 24 characters, so an allowed word could hide a path or a secret right next to it)."""
        if span is None:
            return None
        base = where.split("::")[0].replace(" (file name)", "")
        for rules_ok, glob, rx in self.allow:
            if rules_ok is not None and rule not in rules_ok:
                continue
            if not fnmatch.fnmatch(base, glob):
                continue
            if any(m.end() > m.start() and m.start() <= span[0] and span[1] <= m.end() for m in rx.finditer(text)):
                return (",".join(sorted(rules_ok)) + "::" if rules_ok else "") + f"{glob}::{rx.pattern}"
        return None

    def hit(self, rule, label, where, line_no, line_text, matched, tier="RED", span=None, allow_text=None, value=None):
        """Record a hit. `span` is where the match sits in `allow_text` (default: `line_text`); callers that know it pass
        it, so a second occurrence of the same text is judged on its own. Returns the list it went to."""
        shown = matched[:6] + "…" + f"({len(matched)} chars)" if rule in MASK_RULES else matched
        excerpt = line_text.strip()
        if len(excerpt) > 160:
            i = max(0, excerpt.find(matched[:20]) - 60); excerpt = "…" + excerpt[i:i + 150] + "…"
        if rule in MASK_RULES and matched in excerpt:
            excerpt = excerpt.replace(matched, shown)
        rec = {"rule": rule, "label": label, "where": where, "line": line_no, "match": shown, "excerpt": excerpt}
        if tier == "NOTE":
            if value is not None:
                rec["_value"] = value
            self.note.append(rec); return "note"
        if rule == "R09":
            value = _phone_value(matched)
        if value is not None and rule in VALUE_RULES:
            rec["_value"] = value                # what printed() groups by; never written to --json
        text = line_text if allow_text is None else allow_text
        if span is None:
            pos = text.find(matched) if matched else -1
            span = (pos, pos + len(matched)) if pos >= 0 else None
        by = self.allowed_by(rule, where, text, span)
        if by:
            rec["allowed_by"] = by; self.allowed.append(rec); return "allowed"
        self.red.append(rec); return "red"


def scan_text(rules, res, where, text, inside):
    lines = text.splitlines() or [""]
    for i, line in enumerate(lines, 1):
        # a drive-letter path with forward slashes is R05's finding; R04 keeps quiet there only while R05 itself speaks
        drive = [m.span() for m in rules.r05.finditer(line) if not res.allowed_by("R05", where, line, m.span())]
        for rid, label, rx in rules.text:
            for m in rx.finditer(line):          # every match: a first one that is allowed must not hide the next
                if not m.group(0) or (rid == "R04" and _inside(m.span(), drive)):
                    continue                     # a drive-letter path with forward slashes is R05's, reported once
                after = line[m.end():m.end() + 96]
                standin = _standin_user(rid, m.group(0), after)
                if standin is not None:
                    res.hit(rid, label + ", stand-in user", where, i, line, _standin_shown(m.group(0), standin), tier="NOTE")
                else:
                    res.hit(rid, label, where, i, line, m.group(0), span=m.span(), value=_home_user(rid, m.group(0), after) or None)
        for m in ASSIGNED.finditer(line):
            val = m.group(2)
            if sum(c.isdigit() for c in val) >= 3 and not PLACEHOLDER.search(val):
                res.hit("R08", "assigned secret", where, i, line, val, span=m.span(2))
        test_date_spans = []
        judged = []                              # spans the two patterns above already judged (fiction, or reported)
        area_555 = []                            # spans of +1 numbers in area code 555 (NOTE)
        for rx in PHONES:
            for m in rx.finditer(line):
                if m.group(0).isdigit():
                    continue
                judged.append(m.span())
                if rx is PHONES[1] and _inside(m.span(), area_555):   # the same number again, without its +1: a NOTE as well
                    res.hit("R09", "+1 number in area code 555 (not assignable)", where, i, line, m.group(0), tier="NOTE"); continue
                dated = _test_phone_date_span(line, m)
                if dated:
                    test_date_spans.append(dated)
                    continue
                # Only the second pattern's hit across that same delimiter into the
                # date may be skipped, wholly inside an explicitly excepted match.
                if rx is PHONES[1] and any(start <= m.start() < delimiter and date < m.end() <= end
                                          for start, end, delimiter, date in test_date_spans):
                    continue
                digits = re.sub(r"\D", "", m.group(0))
                if _is_test_number(digits):
                    continue
                if m.group(0).startswith("+") and AREA_555.fullmatch(digits):
                    area_555.append(m.span())
                    res.hit("R09", "+1 number in area code 555 (not assignable)", where, i, line, m.group(0), tier="NOTE")
                else:
                    res.hit("R09", "non-fictional phone number", where, i, line, m.group(0), span=m.span())
        # Scan only the residual text for the new shapes; blank judged spans to
        # avoid interpreting a fiction number's tail as another national number.
        rest = list(line)
        for a, b in judged:
            rest[a:b] = "\x00" * (b - a)
        rest = "".join(rest)
        for m in PHONE_NATIONAL0.finditer(rest):
            digits = re.sub(r"\D", "", m.group(0))
            if NATIONAL0_DIGITS[0] <= len(digits) <= NATIONAL0_DIGITS[1] and not _is_test_national0(digits):
                res.hit("R09", "non-fictional phone number", where, i, line, m.group(0), span=m.span())
        for m in PHONE_CN_MOBILE.finditer(rest):
            res.hit("R09", "non-fictional phone number", where, i, line, m.group(0), span=m.span())
            # The phone-word branch would report the same compact number again.
            # Blank only this reported span, retaining offsets and nearby words.
            rest = rest[:m.start()] + "\x00" * (m.end() - m.start()) + rest[m.end():]
        for m in PHONE_BARE_RUN.finditer(rest):
            if (PHONE_WORD.search(rest[max(0, m.start() - PHONE_WORD_WINDOW):m.start()])
                    and not _is_test_number(m.group(0))):
                res.hit("R09", "non-fictional phone number", where, i, line, m.group(0), span=m.span())
        for m in EMAIL.finditer(line):
            if not EXAMPLE_MAIL.search(m.group(0)):
                local, _, domain = m.group(0).partition("@")
                if _is_version(domain):          # one NOTE record per string; printed() folds a file's records into one line
                    res.hit("R10", "name@version, not an e-mail address", where, i, line, m.group(0), tier="NOTE", value=where); continue
                whole = m.start() == 0 or line[m.start() - 1] in MAIL_EDGE   # else the part before the @ is longer than the match
                if whole and local.lower() in STANDIN_MAIL_LOCAL and domain.lower() in STANDIN_MAIL_DOMAIN:
                    res.hit("R10", "e-mail, stand-in name at a stand-in domain", where, i, line, m.group(0), tier="NOTE"); continue
                res.hit("R10", "non-example e-mail", where, i, line, local[:1] + "***@" + domain, span=m.span(), value=m.group(0))
        if inside:
            m = TOOL_RESIDUE.search(line)
            if m:
                res.hit("R13", "AI tool name inside archive/binary", where, i, line, m.group(0), tier="NOTE")
    if not inside and rules.note_scripts and NONLATIN.search(text):
        n = sum(1 for l in lines if NONLATIN.search(l))
        res.hit("R14", "non-Latin script", where, 0, f"{n} lines", f"{n} lines", tier="NOTE")


BIN_WINDOW = 200        # bytes on either side of a binary hit that an allow REGEX is matched in
BIN_LISTED = 20         # allowed occurrences listed per rule and file; the rest are still checked, just not listed


def scan_bytes(rules, res, where, data):
    """Every occurrence of a rule in a binary is judged on its own. The first one that is not allowed makes the file
    RED for that rule (later ones would not change that, so they are not listed); allowed ones, and home paths with a
    stand-in user (NOTE), are listed up to BIN_LISTED and after that only checked. The window is decoded as UTF-8 with undecodable bytes kept as escapes,
    so an allow REGEX written in any script matches the same text it would match in a text file."""
    def window_of(m):
        lo = max(0, m.start() - BIN_WINDOW)
        start = len(data[lo:m.start()].decode("utf-8", "surrogateescape"))
        return data[lo:m.end() + BIN_WINDOW].decode("utf-8", "surrogateescape"), (start, start + len(m.group(0).decode("utf-8", "surrogateescape")))
    drive = [m.span() for m in rules.r05_b.finditer(data) if not res.allowed_by("R05", where, *window_of(m))]
    for rid, label, rx in rules.bytes:
        listed = noted = 0
        for m in rx.finditer(data):
            if not m.group(0) or (rid == "R04" and _inside(m.span(), drive)):
                continue
            after = data[m.end():m.end() + 96].decode("utf-8", "surrogateescape")
            standin = _standin_user(rid, m.group(0).decode("latin-1"), after)
            if standin is not None:              # a stand-in never ends the search: a real name may follow in the same file
                noted += 1
                if noted <= BIN_LISTED:
                    res.hit(rid, label + ", stand-in user (binary)", where, 0, "", _standin_shown(m.group(0).decode("latin-1"), standin), tier="NOTE")
                continue
            window, span = window_of(m)
            if listed >= BIN_LISTED and res.allowed_by(rid, where, window, span):
                continue
            s = m.group(0)[:200].decode("utf-8", "replace")
            user = _home_user(rid, m.group(0).decode("latin-1"), after) or None
            if res.hit(rid, label + " (binary)", where, 0, s, s, span=span, allow_text=window, value=user) == "red":
                break
            listed += 1
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


def _n(n, word):
    """'1 file', '2 files': a count with its noun in the right number"""
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def exit_code(res):
    return 1 if res.red else 0


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


RULE_LIST = re.compile(r"[RU]\d\d(?:,[RU]\d\d)*")


def parse_allow(items, path):
    """RULES::GLOB::REGEX (RULES a comma list of rule IDs) or GLOB::REGEX (any rule). An entry whose first field is a
    list of rule IDs is read as the three-field form; REGEX may itself contain '::'."""
    out, raw = [], list(items or [])
    if path:
        raw += [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.startswith("#")]
    for it in raw:
        head, sep, rest = it.partition("::")
        if RULE_LIST.fullmatch(head) and "::" in rest:
            glob, _, rx = rest.partition("::")
            rules_ok = frozenset(head.split(","))
        else:
            glob, rx, rules_ok = head, rest, None
        if not sep or not glob or not rx:
            raise ValueError(f"allow entry needs RULES::GLOB::REGEX or GLOB::REGEX: {it}")
        out.append((rules_ok, glob, re.compile(rx)))
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
    # one sample per format added in 0.1.3; each value is split, and obviously not a real key
    ("r07-github-server.txt", b"key gh" b"s_" b"FAKEfake0000FAKEfake0000", {"R07"}, set()),
    ("r07-stripe.txt", b"key sk_" b"live_" b"FAKEfake0000FAKEfake0000", {"R07"}, set()),
    ("r07-npm.txt", b"key np" b"m_" b"FAKEfake0000FAKEfake0000FAKEfake0000", {"R07"}, set()),
    ("r07-gitlab.txt", b"key gl" b"pat-" b"FAKEfake0000FAKEfake", {"R07"}, set()),
    ("r07-sendgrid.txt", b"key S" b"G." b"FAKEfake0000FAKEfake00" b"." b"FAKEfake0000FAKEfake0000FAKEfake0000FAKEfak", {"R07"}, set()),
    ("r07-jwt.txt", b"key ey" b"JhbGciOiJub25lIn0" b"." b"ey" b"JzdWIiOiJmYWtlIn0" b"." b"FAKEfake0000", {"R07"}, set()),
    ("r07-twilio.txt", b"key S" b"K" b"0123456789abcdef0123456789abcdef", {"R07"}, set()),
    ("r07-huggingface.txt", b"key h" b"f_" b"FAKEfake0000FAKEfake0000FAKEfake00", {"R07"}, set()),
    ("r07ok.txt", b"npm_config_cache sk_live_ SKU12345 SG.short.x eyJ.only.one glpat-short hf_hub ghs_x "
                  b"sha 0123456789abcdef0123456789abcdef task-12345678901234567890", set(), {"R07"}),
    ("r08.txt", b'API_KEY = "a1b2c3d4e5f6' b'g7h8i9j0k1l2"', {"R08"}, set()),
    ("r08ok.txt", b'API_KEY = "YOUR_API_KEY_GOES_HERE_12345"\ntoken = localStorage.getItem', set(), {"R08"}),
    ("r09.txt", b"call +1 6" b"04 123 4567", {"R09"}, set()),
    ("r09b.txt", b"call 604-1" b"23-4567 now", {"R09"}, set()),
    ("r09ok.txt", b"+1 202 555 0101 / 604-555-0199 / 020 7946 0123 / 07700 900123 / (202) 555-0199", set(), {"R09"}),
    ("r09c.txt", b"id 2147483648 view/9876543210 ts 1694745600", set(), {"R09"}),
    # 0.1.5 phone cases: split literals keep synthetic RED examples out of the source scan.
    ('r09r2nastop.txt', b'Call m' b'e at 6' b'04-123' b'-4567.', {'R09'}, set()),
    ('r09r2nafictionstop.txt', b'Call 6' b'04-555' b'-0175.', set(), {'R09'}),
    ('r09r2nadecimal.txt', b'value ' b'604-12' b'3-4567' b'.5', set(), {'R09'}),
    ('r09r2natail.txt', b'token ' b'604-12' b'3-4567' b'x', set(), {'R09'}),
    ('r09r2bare10.txt', b'id 604' b'123456' b'7 and ' b'138123' b'4567', set(), {'R09'}),
    ('r09r2cnspace.txt', b'138 12' b'34 567' b'8', {'R09'}, set()),
    ('r09r2cndash.txt', b'138-12' b'34-567' b'8', {'R09'}, set()),
    ('r09r2cnbare.txt', b'138123' b'45678', {'R09'}, set()),
    ('r09r2cnlow.txt', b'130 12' b'34 567' b'8', {'R09'}, set()),
    ('r09r2cnhigh.txt', b'199 12' b'34 567' b'8', {'R09'}, set()),
    ('r09r2cnid.txt', b'id: 13' b'812345' b'678', {'R09'}, set()),
    ('r09r2cnnotna.txt', b'138555' b'50123', {'R09'}, set()),
    ('r09r2cnword.txt', b'\xe6\x89\x8b\xe6\x9c\xba' b'\xef\xbc\x9a138' b'123456' b'78', {'R09'}, set()),
    ('r09r2cnstop.txt', b'Call 1' b'38 123' b'4 5678' b'.', {'R09'}, set()),
    ('r09r2cnprefix.txt', b'128123' b'45678 ' b'and 20' b'812345' b'678', set(), {'R09'}),
    ('r09r2cnlength.txt', b'138123' b'4567 a' b'nd 138' b'123456' b'789', set(), {'R09'}),
    ('r09r2cninside.txt', b'a13812' b'345678' b' ratio' b' 3.138' b'123456' b'78', set(), {'R09'}),
    ('r09r2cntail.txt', b'138123' b'45678x' b' and 1' b'381234' b'5678.5', set(), {'R09'}),
    ('r09r2cngroups.txt', b'138  1' b'234  5' b'678 an' b'd 138 ' b'123 45' b'678', set(), {'R09'}),
    ('r09r2cnfictionbefore.txt', b'+1 385' b' 555 0' b'123 / ' b'138 12' b'34 567' b'8', {'R09'}, set()),
    ('r09r2cnonlynafiction.txt', b'+1 385' b' 555 0' b'123', set(), {'R09'}),
    ('r09tabok.csv', b'+1 (25' b'0) 555' b'-0175\t' b'\t2026-' b'09-16', set(), {'R09'}),
    ('r09spaceok.txt', b'+1 (25' b'0) 555' b'-0175 ' b' 2026-' b'09-16', set(), {'R09'}),
    ('r09auok.txt', b'+61 49' b'1 570 ' b'156', set(), {'R09'}),
    ('r09aumobiles.txt', b'+61 49' b'1 570 ' b'006 / ' b'+61 49' b'1 570 ' b'156 / ' b'+61 49' b'1 570 ' b'157 / ' b'+61 49' b'1 570 ' b'158 / ' b'+61 49' b'1 570 ' b'159 / ' b'+61 49' b'1 570 ' b'110\n+6' b'1 491 ' b'570 31' b'3 / +6' b'1 491 ' b'570 73' b'7 / +6' b'1 491 ' b'571 26' b'6 / +6' b'1 491 ' b'571 49' b'1 / +6' b'1 491 ' b'571 80' b'4 / +6' b'1 491 ' b'572 54' b'9\n+61 ' b'491 57' b'2 665 ' b'/ +61 ' b'491 57' b'2 983 ' b'/ +61 ' b'491 57' b'3 770 ' b'/ +61 ' b'491 57' b'3 087 ' b'/ +61 ' b'491 57' b'4 118 ' b'/ +61 ' b'491 57' b'4 632\n' b'+61 49' b'1 575 ' b'254 / ' b'+61 49' b'1 575 ' b'789 / ' b'+61 49' b'1 576 ' b'398 / ' b'+61 49' b'1 576 ' b'801 / ' b'+61 49' b'1 577 ' b'426 / ' b'+61 49' b'1 577 ' b'644\n+6' b'1 491 ' b'578 95' b'7 / +6' b'1 491 ' b'578 14' b'8 / +6' b'1 491 ' b'578 88' b'8 / +6' b'1 491 ' b'579 21' b'2 / +6' b'1 491 ' b'579 76' b'0 / +6' b'1 491 ' b'579 45' b'5', set(), {'R09'}),
    ('r09aureal.txt', b'+61 41' b'2 345 ' b'678', {'R09'}, set()),
    ('r09aunear.txt', b'+61 49' b'1 570 ' b'155', {'R09'}, set()),
    ('r09tabreal.csv', b'+1 (25' b'0) 234' b'-0175\t' b'\t2026-' b'09-16', {'R09'}, set()),
    ('r09tab555.csv', b'+1 (25' b'0) 555' b'-0275\t' b'\t2026-' b'09-16', {'R09'}, set()),
    ('r09space555.txt', b'+1 (25' b'0) 555' b'-0275 ' b' 2026-' b'09-16', {'R09'}, set()),
    ('r09tabshort.txt', b'+123\t4' b'567890' b'12', {'R09'}, set()),
    ('r09tabtwo.txt', b'+1 (25' b'0) 555' b'-0175\t' b'\t+61 4' b'12 345' b' 678', {'R09'}, set()),
    ('r09spacetwo.txt', b'+1 (25' b'0) 555' b'-0175 ' b' 604-1' b'23-456' b'7', {'R09'}, set()),
    ('r09ausuffix.txt', b'+61 49' b'1 570 ' b'156  0' b'412 34' b'5 678', {'R09'}, set()),
    ('r09natabsuffix.txt', b'+1 (25' b'0) 555' b'-0175\t' b'\t0412 ' b'345 67' b'8', {'R09'}, set()),
    ('r09uksuffix.txt', b'+44 77' b'00 900' b'123  0' b'20 712' b'3 4567', {'R09'}, set()),
    ('r09nasuffix.txt', b'+1 (25' b'0) 555' b'-0175\t' b'\t604 1' b'23 456' b'7', {'R09'}, set()),
    ('r09autabdate.txt', b'+61 49' b'1 570 ' b'156\t20' b'26-09-' b'16', set(), {'R09'}),
    ('r09autimedate.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 10' b':30', set(), {'R09'}),
    ('r09suffixdigits.txt', b'+61 49' b'1 570 ' b'156\t04' b'123456' b'78', {'R09'}, set()),
    ('r09suffixmany.txt', b'+61 49' b'1 570 ' b'156  0' b'412 34' b'5 678\t' b'020 71' b'23 456' b'7  604' b' 123 4' b'567', {'R09'}, set()),
    ('r09suffixfiction.txt', b'+61 49' b'1 570 ' b'156\t04' b'91 570' b' 157\t2' b'026-09' b'-16', {'R09'}, set()),
    ('r09splitarea.txt', b'+1 (25' b'0) 555' b'-0175\t' b'604\t12' b'3-4567', {'R09'}, set()),
    ('r09splitlocal.txt', b'+1 (25' b'0) 555' b'-0175\t' b'604 12' b'3\t4567', {'R09'}, set()),
    ('r09splitbare.txt', b'x 604\t' b'123-45' b'67', {'R09'}, set()),
    ('r09splitintl.txt', b'+1 604' b'\t123\t4' b'567', {'R09'}, set()),
    ('r09suffixnine.txt', b'+61 49' b'1 570 ' b'156\t41' b'2 345 ' b'6789', {'R09'}, set()),
    ('r09datereal.txt', b'+1 (25' b'0) 555' b'-0175\t' b'\t2026-' b'09-16\t' b'604-12' b'3-4567', {'R09'}, set()),
    ('r09datenoise.txt', b'+1 (25' b'0) 555' b'-0175 ' b' 99 20' b'26-09-' b'16 416' b'123456' b'7', {'R09'}, set()),
    ('r09timereal.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 10' b':30\t04' b'12 345' b' 678', {'R09'}, set()),
    ('r09dateinvalid.txt', b'+61 49' b'1 570 ' b'156\t20' b'26-02-' b'30', {'R09'}, set()),
    ('r09timeinvalid.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 25' b':30', {'R09'}, set()),
    ('r09augeo.txt', b'+61 2 ' b'5550 0' b'000 / ' b'+61 2 ' b'5550 9' b'999 / ' b'+61 2 ' b'7010 0' b'000 / ' b'+61 2 ' b'7010 9' b'999\n+6' b'1 3 55' b'50 000' b'0 / +6' b'1 3 55' b'50 999' b'9 / +6' b'1 3 70' b'10 000' b'0 / +6' b'1 3 70' b'10 999' b'9\n+61 ' b'7 5550' b' 0000 ' b'/ +61 ' b'7 5550' b' 9999 ' b'/ +61 ' b'7 7010' b' 0000 ' b'/ +61 ' b'7 7010' b' 9999\n' b'+61 8 ' b'5550 0' b'000 / ' b'+61 8 ' b'5550 9' b'999 / ' b'+61 8 ' b'7010 0' b'000 / ' b'+61 8 ' b'7010 9' b'999', set(), {'R09'}),
    ('r09augeonear.txt', b'+61 2 ' b'5551 1' b'234\n+6' b'1 3 70' b'11 123' b'4\n+61 ' b'7 5540' b' 1234\n' b'+61 8 ' b'7000 1' b'234', {'R09'}, set()),
    ('r09auservice.txt', b'+61 18' b'00 160' b' 401 /' b' +61 1' b'800 97' b'5 707 ' b'/ +61 ' b'1800 9' b'75 708' b' / +61' b' 1800 ' b'975 70' b'9 / +6' b'1 1800' b' 975 7' b'10 / +' b'61 180' b'0 975 ' b'711\n+6' b'1 1300' b' 975 7' b'07 / +' b'61 130' b'0 975 ' b'708 / ' b'+61 13' b'00 975' b' 709 /' b' +61 1' b'300 97' b'5 710 ' b'/ +61 ' b'1300 9' b'75 711', set(), {'R09'}),
    ('r09auservicenear.txt', b'+61 18' b'00 975' b' 706\n+' b'61 130' b'0 975 ' b'712', {'R09'}, set()),
    ('r09n0aumobile.txt', b'0412 3' b'45 678', {'R09'}, set()),
    ('r09n0uk.txt', b'020 71' b'23 456' b'7', {'R09'}, set()),
    ('r09n0dash.txt', b'ring 0' b'412-34' b'5-678 ' b'after ' b'six', {'R09'}, set()),
    ('r09n0dot.txt', b'ring 0' b'412.34' b'5.678 ' b'after ' b'six', {'R09'}, set()),
    ('r09n0tab.txt', b'ring 0' b'412\t34' b'5\t678 ' b'after ' b'six', {'R09'}, set()),
    ('r09n0bareau.txt', b'ring 0' b'412345' b'678 af' b'ter si' b'x', {'R09'}, set()),
    ('r09n0bareuk.txt', b'ring 0' b'207123' b'4567 a' b'fter s' b'ix', {'R09'}, set()),
    ('r09n0brackets.txt', b'(02) 9' b'123 45' b'67', {'R09'}, set()),
    ('r09n0ukmobile.txt', b'07911 ' b'123456', {'R09'}, set()),
    ('r09n0twelve.txt', b'0755-1' b'234 56' b'78', {'R09'}, set()),
    ('r09n0stop.txt', b'Call 0' b'412 34' b'5 678.', {'R09'}, set()),
    ('r09n0afterfiction.txt', b'(202) ' b'555-01' b'01 041' b'2 345 ' b'678', {'R09'}, set()),
    ('r09n0notna.txt', b'0415 5' b'50 112', {'R09'}, set()),
    ('r09n0fictionau.txt', b'0491 5' b'70 156' b' / 049' b'157015' b'6 / 02' b' 5550 ' b'1234 /' b' (03) ' b'7010 0' b'000 / ' b'087010' b'0000', set(), {'R09'}),
    ('r09n0fictionuk.txt', b'020 79' b'46 012' b'3 / 02' b'079460' b'123 / ' b'07700 ' b'900123' b' / 077' b'009001' b'23', set(), {'R09'}),
    ('r09n0fictiontail.txt', b'(250) ' b'555-01' b'75\t604' b'-555-0' b'199', set(), {'R09'}),
    ('r09n0nine.txt', b'x 04 1' b'23 456' b'7', set(), {'R09'}),
    ('r09n0fourteen.txt', b'x 0123' b' 45678' b' 90123', set(), {'R09'}),
    ('r09n0zeros.txt', b'id 000' b'000000' b'0 uuid' b' 00000' b'000-00' b'00-400' b'0-8000' b'-00000' b'000000' b'1 pad ' b'0012 3' b'45 678', set(), {'R09'}),
    ('r09n0inside.txt', b'sha a0' b'412345' b'678 ra' b'tio 3.' b'041234' b'5678', set(), {'R09'}),
    ('r09n0tail.txt', b'041234' b'5678x ' b'and 04' b'123456' b'78.5', set(), {'R09'}),
    ('r09barephone.txt', b'phone:' b' 60412' b'34567', {'R09'}, set()),
    ('r09baretel.txt', b'<a hre' b'f="tel' b':60412' b'34567"' b'>', {'R09'}, set()),
    ('r09barecjk.txt', b'\xe6\x89\x8b\xe6\x9c\xba' b' 60412' b'34567', {'R09'}, set()),
    ('r09baremobile.txt', b'mobile' b' 60412' b'34567', {'R09'}, set()),
    ('r09barecell.txt', b'cell: ' b'604123' b'4567', {'R09'}, set()),
    ('r09barewhatsapp.txt', b'WhatsA' b'pp 604' b'123456' b'7', {'R09'}, set()),
    ('r09barefax.txt', b'fax 60' b'412345' b'67', {'R09'}, set()),
    ('r09baresms.txt', b'SMS 60' b'412345' b'67', {'R09'}, set()),
    ('r09baredianhua.txt', b'\xe7\x94\xb5\xe8\xaf\x9d' b'\xef\xbc\x9a604' b'123456' b'7', {'R09'}, set()),
    ('r09barezhidian.txt', b'\xe8\x87\xb4\xe7\x94\xb5' b' 60412' b'34567', {'R09'}, set()),
    ('r09barefiction.txt', b'phone:' b' 60455' b'50134', set(), {'R09'}),
    ('r09bareeleven.txt', b'\xe6\x89\x8b\xe6\x9c\xba' b'\xef\xbc\x9a138' b'123456' b'78', {'R09'}, set()),
    ('r09barelength.txt', b'phone:' b' 12345' b'6789 a' b'nd pho' b'ne: 12' b'345678' b'9012', set(), {'R09'}),
    ('r09barefar.txt', b'phone ' b'number' b's are ' b'kept i' b'n a li' b'st; ro' b'w 6041' b'234567', set(), {'R09'}),
    ('r09baretail.txt', b'phone ' b'604123' b'4567x ' b'and ph' b'one 60' b'412345' b'67.5 a' b'nd pho' b'ne a60' b'412345' b'67', set(), {'R09'}),
    ('r09bare11other.txt', b'tel: 1' b'204123' b'4567', {'R09'}, set()),
    ('r09bare24.txt', b'phone ' b'      ' b'      ' b'      ' b'604123' b'4567', {'R09'}, set()),
    ('r09bare25.txt', b'phone ' b'      ' b'      ' b'      ' b' 60412' b'34567', set(), {'R09'}),
    ('r09singlespacedate.txt', b'+61 49' b'1 570 ' b'156 20' b'26-09-' b'16', {'R09'}, set()),
    ('r09dateclockseconds.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 10' b':30:45', set(), {'R09'}),
    ('r09dateinvalidclock.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 10' b':61', {'R09'}, set()),
    ('r09datejunk.txt', b'+61 49' b'1 570 ' b'156  2' b'026-09' b'-16 10' b':30 ex' b'tra', {'R09'}, set()),
    ('r09dateoutside.txt', b'+61 49' b'1 570 ' b'156\t20' b'26-09-' b'16 / 6' b'04-123' b'-4567', {'R09'}, set()),
    ('r09aurealdate.txt', b'+61 41' b'2 345 ' b'678\t20' b'26-09-' b'16', {'R09'}, set()),
    ("r10.txt", b"mail bob@" b"realcompany.co", {"R10"}, set()),
    ("r10ok.txt", b"a@example.com b@adapter.invalid 12345+janed@users.noreply.github.com noreply@anthropic.com", set(), {"R10"}),
    ("__pycache__/x.pyc", b"\x00cache", {"R12"}, set()),
    (".DS_Store", b"\x00\x00", {"R12"}, set()),
    (".env", b"X=1", {"R12"}, set()),
    (".env.example", b"X=", set(), {"R12"}),
    ("bin.dat", b"\x00\x01\x2fUsers\x2fsomeone/secret\x00", {"R04"}, set()),
    # 0.1.7: a stand-in user is a NOTE (the note itself is checked in selftest()); a name next to it stays RED
    ("r04standin.txt", b"cd \x2fhome\x2fuser/app\nsee \x2fUsers\x2f.../x and \x2fUsers\x2f<you>/x\nHOME is \x2fhome\x2fnode.\n", set(), {"R04"}),
    ("r05standin.txt", b"C:\x5c\x5cUsers\x5c\x5cYourUsername\x5c\x5capp and C:\x5cUsers\x5cname\x5capp", set(), {"R05"}),
    ("r04standinreal.txt", b"cp \x2fhome\x2fuser/a \x2fUsers\x2fsomeone/b \x2fhome\x2fusers2/c", {"R04"}, set()),
    ("r04short.txt", b"\x2fhome\x2fjo/x\n\x2fUsers\x2fAmy/y\n", {"R04"}, set()),   # a short name is a name: only one character is a stand-in
    ("binstandin.dat", b"\x00\x01\x2fhome\x2fnode/app\x00\x2fUsers\x2fsomeone/secret\x00", {"R04"}, set()),
    ("binstandinonly.dat", b"\x00\x01\x2fhome\x2fnode/app\x00", set(), {"R04"}),
    # 0.1.7: a drive-letter path with forward slashes is R05 only; a path after a URL scheme is still R04
    ("r05fwd.txt", b"C:\x2fUsers\x2fsomeone/proj", {"R05"}, {"R04"}),
    ("r04fileurl.txt", b"open file:\x2fUsers\x2fsomeone/x", {"R04"}, set()),
    ("binfwd.dat", b"\x00\x01C:\x2fUsers\x2fsomeone/proj\x00", {"R05"}, {"R04"}),
    # 0.1.7: name@version is not an address; an address, a login to an IP address and a numeric domain still are
    ("r10version.txt", b"left-pad@" b"1.3.0 and tool@" b"2.0.0-rc.1", set(), {"R10"}),
    ("r10versionreal.txt", b"pkg@" b"1.2.3\nbob@" b"realcompany.co\nroot@" b"10.0.0.5\nx@" b"163.com", {"R10"}, set()),
    # 0.1.7: an address is a NOTE only when both sides are stand-ins
    ("r10standin.txt", b"write to user@" b"company.com or a@" b"b.com", set(), {"R10"}),
    ("r10standinreal.txt", b"user@" b"realcompany.co\nalice@" b"company.com\nuser@" b"gmail.com", {"R10"}, set()),
    # 0.1.7: +1 and area code 555 is a NOTE; without the +1, in another country, or with 555 after a real area code it stays RED
    ("r09area555.txt", b"+1 55" b"5 123" b" 4567\n+1555" b"1234567\n+1 (55" b"5) 867" b"-5309", set(), {"R09"}),
    ("r09area555real.txt", b"call 55" b"5 123" b" 4567\n+1 60" b"4 555" b" 2671\n+90 55" b"5 123" b" 45 67\n+1 55" b"5 123" b" 4567 8", {"R09"}, set()),
    # 0.1.7: repeats of one value are one printed line; the records themselves stay one per place
    ("r10repeat.txt", b"bob@" b"realcompany.co\nbob@" b"realcompany.co\nBOB@" b"realcompany.co\nbill@" b"realcompany.co", {"R10"}, set()),
    ("r09repeat.txt", b"+1 60" b"4 123" b" 4567 or 604-1" b"23-4567", {"R09"}, set()),
    # 0.1.7, after an audit: the whole folder name is judged, spaces included; one character is a name; prose after a stand-in
    # is not part of it; an @ and four numbers is an address whatever follows; values are grouped only when identical;
    # the part before the @ is judged whole
    ("r05space.txt", b"C:\x5cUsers\x5cDev Sharma\x5cDocuments\x5ctax.xlsx\nC:\x5cUsers\x5cJ Okafor\x5cDesktop\x5cp.csv\nC:\x5cUsers\x5cYou Zhang\x5cAppData\x5capp.log", {"R05"}, set()),
    ("binspace.dat", b"\x00\x01C:\x5cUsers\x5cDev Sharma\x5cDocuments\x00", {"R05"}, set()),
    ("r04onechar.txt", b"\x2fhome\x2fj\x2fjokafor/thesis\n\x2fUsers\x2fk/Documents/papers\nC:\x5cUsers\x5c\xe7\xa3\x8a\x5cDesktop", {"R04", "R05"}, set()),
    ("r04prose.txt", b"HOME is \x2fhome\x2fnode. The caller creates \x2fworkspace\x2fgroup first\nsee \x2fUsers\x2fme and \x2fhome\x2fuser for more", set(), {"R04"}),
    ("r10ipsuffix.txt", b"left-pad@" b"1.3.0\nssh admin@" b"192.168.1.10-prod", {"R10"}, set()),
    ("r05twopeople.txt", b"C:\x5cUsers\x5cMaria Lindqvist\x5ca.txt\nC:\x5cUsers\x5cMaria Okafor\x5cb.txt", {"R05"}, set()),
    ("r09collide.txt", b"\xe6\x89\x8b\xe6\x9c\xba 131" b"2345" b"6789\noffice (31" b"2) 345" b"-6789", {"R09"}, set()),
    ("r10nonascii.txt", b"\xe7\x8e\x8ba@" b"b.com and jos\xc3\xa9test@" b"test.com", {"R10"}, set()),
    ("fwdallow.txt", b"C:\x2fUsers\x2fsomeone/proj", {"R05"}, {"R04"}),
    ("r04repeat.txt", b"\x2fUsers\x2fsomeone/a\n\x2fUsers\x2fsomeone/b\n\x2fUsers\x2fother/c\n\x2fVolumes\x2fWork/a\n\x2fVolumes\x2fWork/b", {"R04"}, set()),
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
            if "R09" in must and len(data_lines := next(data for name, data, _, _ in SAMPLES if name == rel).splitlines()) > 1:
                for line_no in range(1, len(data_lines) + 1):
                    check(any(h["where"] == rel and h["line"] == line_no and h["rule"] == "R09" for h in res.red),
                          f"{rel}:{line_no} hits R09 independently")
        cn_word = [h for h in res.red if h["where"] == "r09r2cnword.txt" and h["rule"] == "R09"]
        check(len(cn_word) == 1, "r09r2cnword.txt Chinese phone is reported once")
        # Preserve whole-match reporting for real numbers split across columns.
        split_data = next(data for rel, data, _, _ in SAMPLES if rel == "r09splitarea.txt")
        check(any(h["where"] == "r09splitarea.txt" and h["rule"] == "R09"
                  and h["match"] == split_data.decode() for h in res.red),
              "r09splitarea.txt retains the whole run-on match")
        def notes(rel, rule):
            return [n for n in res.note if n["where"] == rel and n["rule"] == rule]
        def reds(rel, rule):
            return [r for r in res.red if r["where"] == rel and r["rule"] == rule]
        check(len(notes("r04standin.txt", "R04")) == 4, f"r04standin.txt: four stand-in users are four NOTEs (got {len(notes('r04standin.txt', 'R04'))})")
        check(len(notes("r05standin.txt", "R05")) == 2, f"r05standin.txt: two stand-in Windows users are two NOTEs (got {len(notes('r05standin.txt', 'R05'))})")
        check(len(reds("r05space.txt", "R05")) == 3 and not notes("r05space.txt", "R05"), f"r05space.txt: a folder name with a space is judged whole, never by its first word (got {len(reds('r05space.txt', 'R05'))} RED)")
        check(len(reds("binspace.dat", "R05")) == 1 and not notes("binspace.dat", "R05"), "binspace.dat: the same in a binary")
        check(len(reds("r04onechar.txt", "R04")) == 2 and len(reds("r04onechar.txt", "R05")) == 1, "r04onechar.txt: a one-character folder is a name, in any script, and so is a home filed under its first letter")
        check(len(notes("r04prose.txt", "R04")) == 3, f"r04prose.txt: prose after a stand-in is not part of the name (got {len(notes('r04prose.txt', 'R04'))} NOTEs)")
        check(len(reds("r10ipsuffix.txt", "R10")) == 1 and len(notes("r10ipsuffix.txt", "R10")) == 1, f"r10ipsuffix.txt: an @ and four numbers stays RED whatever follows; the version next to it is a NOTE (got {len(reds('r10ipsuffix.txt', 'R10'))} RED)")
        check(len(reds("r10nonascii.txt", "R10")) == 2, f"r10nonascii.txt: an address is judged on its whole part before the @ (got {len(reds('r10nonascii.txt', 'R10'))} RED)")
        ra = scan_tree(rules, d, parse_allow(["R05::fwdallow.txt::C:.Users."], None))
        check("R05" in {x["rule"] for x in ra.allowed if x["where"] == "fwdallow.txt"} and "R04" in {x["rule"] for x in ra.red if x["where"] == "fwdallow.txt"},
              "fwdallow.txt: when an allow entry takes the R05 finding away, R04 still reports the path")
        check(len(reds("r04standinreal.txt", "R04")) == 2 and len(notes("r04standinreal.txt", "R04")) == 1,
              "r04standinreal.txt: a stand-in on a line is a NOTE, the two names on the same line stay RED")
        check(len(reds("r04short.txt", "R04")) == 2, f"r04short.txt: two- and three-letter names stay RED (got {len(reds('r04short.txt', 'R04'))})")
        check(len(notes("binstandin.dat", "R04")) == 1, "binstandin.dat: the stand-in before the name is a NOTE, and the search goes on to the name")
        check(len(notes("binstandinonly.dat", "R04")) == 1, "binstandinonly.dat: a stand-in user in a binary is a NOTE")
        check(len(reds("r05fwd.txt", "R05")) == 1, "r05fwd.txt: a drive-letter path with forward slashes is one finding")
        ver = notes("r10version.txt", "R10")
        check(len(ver) == 2 and [c for _, c, _ in printed(ver)] == [2], f"r10version.txt: two name@version strings are two NOTE records, printed as one line that counts them (got {len(ver)})")
        check(len(reds("r10versionreal.txt", "R10")) == 3 and len(notes("r10versionreal.txt", "R10")) == 1,
              f"r10versionreal.txt: the address, the login to an IP address and the numeric domain stay RED (got {len(reds('r10versionreal.txt', 'R10'))} RED)")
        check(len(notes("r10standin.txt", "R10")) == 2, f"r10standin.txt: two addresses with a stand-in on both sides are two NOTEs (got {len(notes('r10standin.txt', 'R10'))})")
        check(len(reds("r10standinreal.txt", "R10")) == 3, f"r10standinreal.txt: a stand-in on one side only stays RED (got {len(reds('r10standinreal.txt', 'R10'))} RED)")
        check(len(notes("r09area555.txt", "R09")) == 5, f"r09area555.txt: three +1 numbers in area code 555 are NOTEs, and so is each one's second match without the +1 (got {len(notes('r09area555.txt', 'R09'))})")
        def lines_of(rel, rule):
            return sorted(count for r, count, _ in printed(reds(rel, rule)))
        check(len(reds("r10repeat.txt", "R10")) == 4 and lines_of("r10repeat.txt", "R10") == [1, 1, 2],
              f"r10repeat.txt: four records, three printed lines; only the identical address is folded (got {lines_of('r10repeat.txt', 'R10')})")
        check(lines_of("r09repeat.txt", "R09") == [1, 2],
              f"r09repeat.txt: the same ten digits twice are one printed line; the eleven-digit form is its own (got {lines_of('r09repeat.txt', 'R09')})")
        check(lines_of("r05twopeople.txt", "R05") == [1, 1], f"r05twopeople.txt: two people who share a first name are two lines (got {lines_of('r05twopeople.txt', 'R05')})")
        check(lines_of("r09collide.txt", "R09") == [1, 1], f"r09collide.txt: an eleven-digit number and a ten-digit one are never one value (got {lines_of('r09collide.txt', 'R09')})")
        check(len(reds("r04repeat.txt", "R04")) == 5 and lines_of("r04repeat.txt", "R04") == [1, 1, 1, 2],
              f"r04repeat.txt: one line per home-path user; a path that is not a home path is never grouped (got {lines_of('r04repeat.txt', 'R04')})")
        check(all("_value" not in r for r in public(res.red) + public(res.note)) and any("_value" in r for r in res.red), "--json records carry no grouping value")
        check("R12" in by_where.get("__pycache__/", set()), "__pycache__/ directory itself is R12")
        check(exit_code(res) == 1, "a scan with RED hits exits 1")
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
        # 0.1.2: an entry must cover the matched text itself, rule by rule, and every occurrence is judged on its own
        def at(r, name, tier):
            return {x["rule"] for x in getattr(r, tier) if x["where"].startswith(name)}
        open(os.path.join(d, "near.txt"), "wb").write(b"owner janedoe1987 wrote \x2fUsers\x2fsynthetic/private.txt")
        r5 = scan_tree(rules, d, parse_allow(["near.txt::janedoe1987"], None))
        check(at(r5, "near.txt", "allowed") == {"U01"} and "R04" in at(r5, "near.txt", "red"),
              f"an allowed word right next to a path does not allow the path (red {sorted(at(r5, 'near.txt', 'red'))})")
        open(os.path.join(d, "twice.txt"), "wb").write(b"janedoe1987 and later janedoe1987")
        r6 = scan_tree(rules, d, parse_allow(["twice.txt::janedoe1987 and"], None))
        check("U01" in at(r6, "twice.txt", "allowed") and "U01" in at(r6, "twice.txt", "red"),
              "two matches of one rule on a line: the entry covers the first, the second stays RED")
        open(os.path.join(d, "scoped.txt"), "wb").write(b"see \x2fUsers\x2fsynthetic/janedoe1987.txt")
        r7 = scan_tree(rules, d, parse_allow(["R04::scoped.txt::\x2fUsers\x2fsynthetic/janedoe1987\\.txt"], None))
        r7b = scan_tree(rules, d, parse_allow(["scoped.txt::\x2fUsers\x2fsynthetic/janedoe1987\\.txt"], None))
        check("R04" in at(r7, "scoped.txt", "allowed") and "U01" in at(r7, "scoped.txt", "red")
              and {"R04", "U01"} <= at(r7b, "scoped.txt", "allowed"),
              "RULES::GLOB::REGEX allows only the named rule; the same REGEX without RULES allows both hits it covers")
        pa = parse_allow(["R04,U01::a.txt::x::y", "a.txt::x"], None)
        try:
            parse_allow(["no separator here"], None); bad_refused = False
        except ValueError:
            bad_refused = True
        check(pa[0][0] == frozenset({"R04", "U01"}) and pa[0][1] == "a.txt" and pa[0][2].pattern == "x::y"
              and pa[1][0] is None and bad_refused,
              "allow entries: three-field and two-field forms parse, REGEX may contain '::', a malformed entry is refused")
        open(os.path.join(d, "bin1.dat"), "wb").write(b"\x00\x01janedoe1987 \x2fUsers\x2fsynthetic/private\x00\x02")
        r8 = scan_tree(rules, d, parse_allow(["bin1.dat::janedoe1987"], None))
        check(at(r8, "bin1.dat", "allowed") == {"U01"} and "R04" in at(r8, "bin1.dat", "red"),
              "in a binary, an allowed word right next to a path does not allow the path")
        open(os.path.join(d, "bin2.dat"), "wb").write(b"\x00janedoe1987-ok\x00" + b"x" * 300 + b"\x00janedoe1987\x00")
        r9 = scan_tree(rules, d, parse_allow(["bin2.dat::janedoe1987-ok"], None))
        check("U01" in at(r9, "bin2.dat", "allowed") and "U01" in at(r9, "bin2.dat", "red"),
              "in a binary, a second occurrence of an allowed rule is judged on its own")
        open(os.path.join(d, "bin3.dat"), "wb").write(b"\x00" + b"janedoe1987-ok\x00" * (BIN_LISTED + 5) + b"janedoe1987\x00")
        r10 = scan_tree(rules, d, parse_allow(["bin3.dat::janedoe1987-ok"], None))
        n_listed = sum(1 for x in r10.allowed if x["where"].startswith("bin3.dat"))
        check("U01" in at(r10, "bin3.dat", "red") and n_listed == BIN_LISTED,
              f"in a binary, past the {BIN_LISTED} listed allowed occurrences a real one is still found (listed {n_listed})")
        rules_ns = Rules(FAKE_CFG, note_scripts=True)
        open(os.path.join(d, "ru.md"), "wb").write("привет".encode("utf-8"))
        res3 = scan_tree(rules_ns, d, [])
        check(any(n["rule"] == "R14" for n in res3.note) and not any(r["rule"] == "R14" for r in res3.red), "--note-scripts: non-Latin text is NOTE, never RED")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "ok.md"), "w").write("# fine\n")
        res = scan_tree(rules, d, [])
        check(not res.red and res.n_files == 1, f"clean directory: 0 RED ({res.n_files} file scanned)")
        check(exit_code(res) == 0, "a scan with no RED hit exits 0")
    with tempfile.TemporaryDirectory() as d:
        def g(*a):   # the identity goes in through git's own options, not through a copy of the environment
            subprocess.run(["git", "-C", d, "-c", "user.name=j", "-c", "user.email=12345+janed@users.noreply.github.com", *a],
                           check=True, capture_output=True)
        g("init", "-q"); open(os.path.join(d, "k.txt"), "w").write("token = 'ghp_abcdefghij" "klmnopqrstuvwxyz1234'\n")
        g("add", "k.txt"); g("commit", "-q", "-m", "add key")
        os.remove(os.path.join(d, "k.txt")); g("rm", "-q", "k.txt"); g("commit", "-q", "-m", "remove key")
        open(os.path.join(d, "n.txt"), "w").write("clean\n"); g("add", "n.txt")
        g("commit", "-q", "-m", "note", "--author=j <jane@" "gmail.com>")
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
        print(f"git range {a.git_range}: {_n(n_c, 'commit')}, {_n(n_b, 'blob')} scanned")
    print(f"scanned {a.dir}: {_n(res.n_files, 'file')} · {res.n_text} text · {res.n_bytes} binary · {_n(res.n_members, 'archive member name')} · {_n(res.n_pdf, 'PDF stream')}")
    for title, rows in (("RED", res.red), ("ALLOWED", res.allowed), ("NOTE", res.note)):
        shown = printed(rows)
        repeats = "" if len(shown) == len(rows) else f", printed as {_n(len(shown), 'line')}: a repeated value is one line with its count, --json lists every place"
        print(f"{title} ({len(rows)}{repeats}):")
        for r, count, files in shown:
            print(f"  [{r['rule']} {r['label']}] {r['where']}:{r['line']}  {r['match']}   | {r['excerpt'][:120]}" + (f"   allowed by {r['allowed_by']}" if 'allowed_by' in r else "")
                  + (f"   × {count} in {_n(len(files), 'file')}, the first is shown" if count > 1 else ""))
    print(f"UNSCANNED ({len(res.unscanned)}):" + ("" if res.unscanned else " none"))
    for u in res.unscanned:
        print(f"  {u}")
    verdict = "RED" if res.red else "GREEN"
    print(f"verdict: {'🔴 RED — do not publish' if res.red else '🟢 GREEN — NOTE items still need a human look'}")
    if a.json:
        json.dump({"stamp": stamp, "dir": os.path.abspath(a.dir), "config": cfg_path, "git_range": a.git_range, "red": public(res.red),
                   "allowed": public(res.allowed), "note": public(res.note), "unscanned": res.unscanned, "verdict": verdict}, open(a.json, "w"), indent=1, ensure_ascii=False)
    return exit_code(res)


if __name__ == "__main__":
    sys.exit(main())
