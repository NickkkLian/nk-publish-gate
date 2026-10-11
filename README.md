# nk-publish-gate

An agent skill for [Claude Code](https://code.claude.com) and [OpenAI Codex](https://developers.openai.com/codex). A local privacy check before a directory or selected Git history goes public: finds recognized patterns such as home-directory paths inside xlsx files, usernames in Python bytecode and personal addresses.

**What you get.** Two planted examples of personal-data patterns outside usual credential rules: a home-directory path in a text file inside a zip inside an xlsx, and the path a `.pyc` records for the file it was compiled from. A real run of nk-publish-gate 0.1.8 on 2026-10-11:

![nk-publish-gate: a real run. RED (4): a cache folder; a home path in a text file inside a zip inside an xlsx; a .pyc; and the home path that .pyc records for the file it was compiled from. Verdict: RED, do not publish](https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/results/nk-publish-gate.png)

It is a picture because this README has to pass the same gate, and two of the red lines quote a home path. The run as text is what the last command under [Try it](#try-it) prints.

That folder is planted. In the trial of 20 public repositories, the reader labelled home paths as real account names in 6 repositories and an address as personal and undeclared in 1 repository. The gate also said RED on 11 more repositories, 10 of them only on occurrences labelled false alarms. These are the reader's text-only judgements: see [What RED meant on 20 real repositories](#what-red-meant-on-20-real-repositories) and [Settle a false alarm in one line](#settle-a-false-alarm-in-one-line).

![nk-publish-gate](https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/social/nk-publish-gate.png)

Part of [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) — skills that stop an AI coding agent's
"done, tested, safe" from being taken on faith.

## What RED meant on 20 real repositories

The gate was run on 20 public skill repositories chosen by a rule written down before anything was downloaded. The selection details and list are kept with the trial's notes and are not given here, so that no repository is pointed at. Version 0.1.7 said RED on 18 of them and printed 360 RED folded lines for 1,011 RED finding occurrences. On 2026-10-10 every distinct value was read and sorted by written rules (the 873 e-mail and phone findings are 259 distinct values, each read once with up to three of its places), by one reader (an AI agent) with no second reader, from the text only: nobody tested whether an address, a number or a key is live, and the working trees were scanned, not the commit history.

How the reader labelled the 18 RED repository verdicts (counts here are repositories):

- **6 repositories** had home paths labelled as carrying a real account name.
- **1 repository** had an address judged to look personal and undeclared by the project.
- **1 repository** had only addresses the reader could not decide.
- **10 repositories** were RED only on occurrences labelled false alarms: values judged invented, not addresses or numbers, or declared public contacts. Among these, 21 finding occurrences (7 distinct addresses) were at a personal mail provider: 13 occurrences in manifest author fields and 8 in third-party licence lines. The reader judged those contacts intentionally public; the text does not establish mailbox ownership or consent.

All counts in the following table are RED finding occurrences in JSON, not distinct addresses, accounts or people. The right column records the reader's labels, not independently verified ownership or consent.

| Rule | RED finding occurrences | What the reader took them for |
|---|---|---|
| E-mail address | 814 | 397 judged declared public contacts (375 project-associated, 22 inside bundled or quoted work); 23 of those at a personal mail provider; 339 judged invented; 52 judged not addresses (chat ids, package names, the login part of a URL); 11 judged role addresses of a service; 2 on example-reserved domains; 8 undecided; 5 occurrences of the address judged personal and undeclared above |
| Home path | 67 | 27 labelled real account names; 22 with a one-character folder, 11 labelled invented personas, 7 with no user folder |
| Key-shaped string | 66 | none looked real: 40 made up in tests and fixtures, 16 a scanner's own samples, 5 a vendor's documented example, 5 made up in docs or source |
| Phone number | 59 | none looked real: 24 not phone numbers, 11 in fiction ranges 0.1.7 does not know, 17 fiction by convention only (2 of them toll-free numbers that can be assigned), 7 invented digit patterns |
| Junk file or folder | 5 | 2 editor folders, a byte-code cache and its `.pyc`, a local settings file |

Of the 27 home-path occurrences labelled real, 23 were in Markdown, 2 in a Python test, 1 in JSON and 1 inside a `.pyc`. So in this trial the reading of archives and compiled files found one labelled occurrence that plain source-text search would ordinarily miss.

In this trial, 32 of the 1,011 RED finding occurrences were labelled real and 8 were undecidable; the remaining occurrences were labelled false alarms. These are text-only judgements. On your own material, inspect each finding and its source; settle only the named false alarms or intentionally public values the person explicitly approves. Remove or otherwise resolve actual private material, and leave undecidable findings RED pending a decision. Never approve an actual credential. These twenty repositories do not establish a rate for other projects.

In the recorded independent comparison of 0.1.8, all 10 repositories labelled RED only on false alarms turned GREEN after 295 settling decisions (median 8 decisions per repository; one needed more than 200). Each decision is one exact rule/value/source-file group. Every finding occurrence labelled real or undecidable stayed RED, and all 5,876 finding occurrences of 0.1.7 are still reported. Decisions were counted; nobody timed a person. The independent checks were run by AI agents that did not write the change.

## Settle a false alarm in one line

In 0.1.8, every RED finding prints `settle:` followed by an entry. Copy everything after `settle:` into one
quoted `--approve` argument; omit the label and surrounding whitespace. Type no private value and escape
nothing inside the entry. It covers that rule and exact value in that file, including repeats on another line. Another
value or another file stays RED. Keys and e-mail addresses stay masked. A home path prints the whole account
folder, so an approval of `alice` cannot cover `alicewong`. It covers other subpaths and future occurrences of
that account in the same file, not the surrounding context. Open the source when masked findings are ambiguous.

From the skill folder (the one containing `scripts/`), start with a fresh `shop` folder. These are invented
fixtures, assembled from pieces in the shell so this README contains no complete token or e-mail address.
The empty demo config makes this example independent of personal config; use your own config for a real
publication scan.

```sh
printf '{}\n' > demo-config.json
mkdir -p shop
printf 'SLACK_TOKEN = "%s%s"  # invented fixture\n' 'xoxb-' 'fake-bot-token' > shop/notify.py
at=@
printf 'project mailbox: maintainers%scontoso.com\n' "$at" > shop/profile.md
python3 scripts/publish_gate.py shop --config demo-config.json --json first.json
```

```text
publish_gate 0.1.8 selftest · 2026-10-11 00:34:47 · 312/312 passed
config: demo-config.json
scanned shop: 2 files · 2 text · 0 binary · 0 archive member names · 0 PDF streams
RED (2):
  [R07 secret shape] notify.py:1  xoxb-f…(19 chars)   | SLACK_TOKEN = "xoxb-f…(19 chars)"  # invented fixture
    Real if this is a credential or private key; remove or rotate it rather than approve it.
    settle: SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995
  [R10 non-example e-mail] profile.md:1  m***@contoso.com   | project mailbox: m***@contoso.com
    Real if this address identifies a mailbox that should stay private.
    settle: SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c
ALLOWED (0):
NOTE (0):
UNSCANNED (0): none
verdict: 🔴 RED — do not publish
```

The first scan exits 1. At a terminal, run `python3 scripts/publish_gate.py shop --config demo-config.json --settle`:
it shows each finding once, asks yes/no, and asks for a reason for each yes. A no stays RED. Never approve an actual
credential. For an agent, first show the person the findings and ask which named findings they approve. Then name
only those findings, one by one with repeated `--approve` flags. Here the person approved exactly these two
invented fixtures. A successful partial settlement still exits 1 if any RED remains; a pass with no RED exits 0.
Invalid input exits 2. Here both current RED findings were approved:

```sh
python3 scripts/publish_gate.py shop --config demo-config.json \
  --approve 'SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995' \
  --approve 'SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c' \
  --reason 'invented documentation fixtures' --json second.json
```

```text
publish_gate 0.1.8 selftest · 2026-10-11 00:34:48 · 312/312 passed
config: demo-config.json
scanned shop: 2 files · 2 text · 0 binary · 0 archive member names · 0 PDF streams
RED (2):
  [R07 secret shape] notify.py:1  xoxb-f…(19 chars)   | SLACK_TOKEN = "xoxb-f…(19 chars)"  # invented fixture
    Real if this is a credential or private key; remove or rotate it rather than approve it.
    settle: SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995
  [R10 non-example e-mail] profile.md:1  m***@contoso.com   | project mailbox: m***@contoso.com
    Real if this address identifies a mailbox that should stay private.
    settle: SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c
ALLOWED (0):
NOTE (0):
UNSCANNED (0): none
verdict: 🔴 RED — do not publish
settling: appended 2 entries to shop/.publish-gate-allow
RED (0):
ALLOWED (2):
  [R07 secret shape] notify.py:1  xoxb-f…(19 chars)   | SLACK_TOKEN = "xoxb-f…(19 chars)"  # invented fixture   allowed by SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995
    reason: invented documentation fixtures
  [R10 non-example e-mail] profile.md:1  m***@contoso.com   | project mailbox: m***@contoso.com   allowed by SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c
    reason: invented documentation fixtures
NOTE (0):
UNSCANNED (0): none
verdict: 🟢 GREEN — NOTE items still need a human look
```

The settling pass exits 0 and appends two dated decisions with the given reason to `shop/.publish-gate-allow`.
An appended approval records a publication decision, not proof that a credential is safe.
It preserves existing entries and comments. Each entry carries the rule, a full SHA-256 of the exact file/location
and a full SHA-256 of the matched value, so even a key-shaped filename cannot put the key into the allow file.
The allow file is read automatically on the next run:

```sh
python3 scripts/publish_gate.py shop --config demo-config.json
```

```text
publish_gate 0.1.8 selftest · 2026-10-11 00:34:48 · 312/312 passed
config: demo-config.json
allow file: shop/.publish-gate-allow · 2 entries read
scanned shop: 3 files · 3 text · 0 binary · 0 archive member names · 0 PDF streams
RED (0):
ALLOWED (2):
  [R07 secret shape] notify.py:1  xoxb-f…(19 chars)   | SLACK_TOKEN = "xoxb-f…(19 chars)"  # invented fixture   allowed by SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995
    reason: invented documentation fixtures
  [R10 non-example e-mail] profile.md:1  m***@contoso.com   | project mailbox: m***@contoso.com   allowed by SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c
    reason: invented documentation fixtures
NOTE (0):
UNSCANNED (0): none
verdict: 🟢 GREEN — NOTE items still need a human look
```

That scan exits 0. Add another value to the same file, then scan again:

```sh
at=@
printf 'new mailbox: reviewers%scontoso.com\n' "$at" >> shop/profile.md
python3 scripts/publish_gate.py shop --config demo-config.json --json third.json
```

```text
publish_gate 0.1.8 selftest · 2026-10-11 00:34:49 · 312/312 passed
config: demo-config.json
allow file: shop/.publish-gate-allow · 2 entries read
scanned shop: 3 files · 3 text · 0 binary · 0 archive member names · 0 PDF streams
RED (1):
  [R10 non-example e-mail] profile.md:2  r***@contoso.com   | new mailbox: r***@contoso.com
    Real if this address identifies a mailbox that should stay private.
    settle: SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 69c514ad8a2d8f385ac4fc281210b60535338f0312d0579250f65afcef82bf3d
ALLOWED (2):
  [R07 secret shape] notify.py:1  xoxb-f…(19 chars)   | SLACK_TOKEN = "xoxb-f…(19 chars)"  # invented fixture   allowed by SHA256 R07 948dcf658d5dfcf8fa520f4846ca97c82d76926ff0e8720836596a3bd7a2c1d8 1fc6256477ce11859e5b2c71847fd138c3ddad821cef493949711c56935e0995
    reason: invented documentation fixtures
  [R10 non-example e-mail] profile.md:1  m***@contoso.com   | project mailbox: m***@contoso.com   allowed by SHA256 R10 74082678e68059ddf4d2396c0e9f3820f1a29d3a93ed329aa02e6a0a50349c2f 068252202ad22260035cdb4d7c51b120503b18bbaf76fea0f2b75fc479171b0c
    reason: invented documentation fixtures
NOTE (0):
UNSCANNED (0): none
verdict: 🔴 RED — do not publish
```

Only the added value is RED; the exit code is 1. Timestamps vary on your run.

Use `--ignore-default-allow` to ignore the default file's decisions. `--allow-file F` reads an additional file and
chooses it as the append destination. An entry can also be copied to a file or passed with `--allow 'ENTRY'`.
Unused entries are named. Whole-line comments may be indented; inline comments are refused explicitly.

Existing regex entries still match as before, including prefixes and `contact.md::.*`; they can cover many values
and are marked WIDE. New digest entries have exact file scope. Use `--scope-all-files` only if the person explicitly
approves that same rule/value in every file; it produces a visible WIDE entry and cannot approve other values.
There is no approve-everything switch. ALLOWED remains in the report, and comments in the allow file are scanned:
pasting a key into a reason still makes the gate RED, even in a loaded allow file outside the scanned root.
Every file-specific ALLOWED decision shows its stored reason, with keys/e-mails masked; missing reasons say
"not recorded". GREEN means no unapproved RED match under these rules in scanned material; NOTE and UNSCANNED
can remain. It does not mean every byte was inspected or every credential detected. This is a static scan:
values assembled at runtime are not reconstructed. Scan generated artifacts too if they will be published.
The directory scan excludes `.git`; add `--git-range` for selected history. See the config guide for the
encoding, archive, assignment-threshold and other boundaries.

Quieter rules were tried and dropped. On 2026-10-10 three builds were measured on the same 20: they turned 6, 8 and 5 of them green (0.1.7: 2), printed 117, 110 and 187 folded RED lines, and kept every occurrence labelled real. But against new values written to test them, each let through some that must stay RED: the first 6 of 7, the second 11 of 55, the third 9 of 48 new ones and none of the earlier 55. The first two let through a complete private key written as quoted lines; the third did not. So those quieter builds were dropped; false alarms require named publication decisions.

## Try it

Python 3.9+ and Git on PATH are prerequisites. Python imports are standard-library only, but every scan's
self-test creates temporary files and Git repositories. The `--selftest` output begins with the displayed
version/date/pass-count line, then lists every check; timestamps vary. This build was tested on Python 3.13.9.

Nothing is installed and nothing under `~/.claude` changes: clone, run the self-test, run the example. Example files are written inside the clone; self-tests also create temporary files and Git repositories.

```bash
git clone https://github.com/NickkkLian/nk-publish-gate && cd nk-publish-gate
python3 scripts/publish_gate.py --selftest
mkdir -p demo/__pycache__ && printf 'print(1)\n' > demo/job.py
python3 -c "import io, zipfile; inner = io.BytesIO(); zipfile.ZipFile(inner, 'w').writestr('notes/todo.txt', 'export of /Users' + '/jane/Clients/acme/q3.xlsx'); zipfile.ZipFile('demo/book.xlsx', 'w').writestr('xl/embeddings/inner.zip', inner.getvalue())"
python3 -c "import py_compile; py_compile.compile('demo/job.py', cfile='demo/__pycache__/job.pyc', dfile='/Users' + '/jane/work/job.py')"
python3 scripts/publish_gate.py demo
```

The self-test output begins with:

```text
publish_gate 0.1.8 selftest · 2026-10-11 00:34:52 · 312/312 passed
```

The last command prints what the picture at the top of this page shows; its last line is the one below, and its exit code is 1 (non-zero on purpose: it found something).

```text
verdict: 🔴 RED — do not publish
```

## What it does

- Checks recognized home-directory paths, e-mail addresses and configured names: in a text file inside a zip inside an xlsx, in a PDF stream, in a `.pyc`, in a commit's author line. None of these is a credential, so a secret pattern need not belong to usual credential rules; configurable scanners can have custom rules. It cannot tell a person's address from an invented one. E-mail exclusions use the exact `EXAMPLE_MAIL` policy and stand-in lists; `no-reply` is not the excluded local part `noreply`.
- Opens archives (zip/xlsx/docx/pptx) three levels deep, member names included; inflates PDF streams; applies byte patterns to binaries; scans directory files regardless of extension, excluding `.git`.
- `--git-range` adds selected commits' authors/committers, messages and added/modified blobs. The default scans no history; HEAD includes its reachable commits, not every branch/tag. Choose the refs you intend to share.
- Your own identifiers live in a config outside every repo; built-in rules work without it.
- For secrets it is a backstop, not a scanner: fourteen key formats and `api_key = <long value>`-style assignments. Run gitleaks or trufflehog as well; what this gate adds is everything on this list that is not a credential.
- Every RED finding supplies an exact, file-scoped SHA-256 allow entry. A terminal `--settle` pass asks yes/no and a reason; agents repeat `--approve 'ENTRY'` only for findings the person named, with `--reason 'why'`. Decisions append to `.publish-gate-allow` at the scanned root, which is read automatically next time. Copy everything after the printed `settle:` into one quoted argument. Keys and e-mail addresses stay masked. Each file-specific ALLOWED decision reached by the scan shows its stored reason; missing reasons say "not recorded". Non-entry content of all loaded allow files is scanned, including outside the root and after append. Partial settlement exits 1 when RED remains; no RED exits 0; invalid input exits 2. Legacy regex forms still match as before; wide and unused entries are named. See [the config guide](references/config-guide.md) for commands and scope.
- Self-test with one sample per rule and per key format, and a clean control.
- A home path is a NOTE, not RED, when its whole user folder name is a stand-in word (`user`, `you`, `dev`, `node` and four more), three dots or a name in angle brackets. Other recognized accounts are RED unless approved, including invented ones such as `jane`. The Linux home-prefix pattern requires an ASCII A–Z/a–z initial; non-ASCII initials can pass without a configured rule. A real account named like a stand-in is a NOTE too: put your login in the config.
- Also NOTEs: a package name with an `@` and a version number (each one is in `--json`, one printed line per file), an e-mail address whose two sides are both stand-ins from two short lists, and a phone number written with `+1` and area code 555, which NANPA lists as not assignable. An `@` followed by four numbers stays RED. A Windows path with forward slashes is one finding, not two.
- Identical matched values in the same file print as one RED decision; another file needs another approval. A settling pass lists every distinct approved binary decision and its reason in the report and JSON, even if RED remains. An ordinary run stops that rule's scan of that file at its first unapproved RED, which stays visible, so it lists only approved decisions reached before that RED; if the file has no RED for that rule, it lists them all. Beyond the binary listing budget of 20 per rule, repeats reached by the scan count on retained ALLOWED records; JSON's optional `occurrences` gives that count (absent means 1), and each printed decision totals it. NOTE keeps its 20-record binary cap. Home paths print the whole account folder; approving `alice` never approves `alicewong`, but covers other subpaths and future occurrences of the same account in that file. Uppercase ASCII Linux account initials now follow the same path rule.
- In the 0.1.6-to-0.1.7 comparison on 20 public skill repositories the RED lines printed fell from 5,560 to 360, and for the median repository from 23 to 7.5. Every 0.1.6 finding is still in `--json`, as RED or as a NOTE. The 28 home-path findings labelled as carrying a real account name and the 66 key-shaped occurrences selected by the reader in the first run are all still RED (the 28 print as 27, because a Windows path that two rules both reported is now counted once); e-mail addresses and phone numbers were not part of that hand-picked set. What the 360 lines turned out to be, read one by one, is under "What RED meant on 20 real repositories".
- Phone checks include leading-zero national forms, phone-word bare 10/11-digit runs, and Chinese national mobiles (11 digits starting 13–19, including matching IDs). Bare ten-digit runs without a phone word stay clean. North American numbers followed by a full stop are caught; documented North American, UK and Australian fiction shapes are exempt, including a test number followed by a column delimiter and a valid ISO date/time. Extra fields and split real numbers stay RED.

The full procedure, the boundaries and where the rules came from are in [SKILL.md](SKILL.md).

## Next to gitleaks and trufflehog

For secrets, use a secret scanner. [gitleaks](https://github.com/gitleaks/gitleaks) and trufflehog know far more key formats than this
gate; gitleaks reads the git history, and with `--max-archive-depth` it opens nested archives too (its README, read 2026-10-01). This
gate's secret rule is a backstop (fourteen formats). This gate also checks personal-data patterns outside usual credential rules;
configurable scanners can have custom rules. These examples include a home-directory path inside an xlsx or a PDF stream, a username in a `.pyc`, a personal
mailbox as commit author, and your own names and handles from a config. gitleaks was not installed or run next to this gate, so no
head-to-head result is claimed.

## How it works

1. Scan the directory that represents the material you will share, and select the history range separately.
2. Read the four lists in order: RED, ALLOWED, NOTE and UNSCANNED.
3. GREEN means RED is empty under these rules in the material scanned.
4. History is dirty and must stay public? Decide with `references/history-decision.md` before rewriting.
5. After the push, clone from the public URL and scan the clone once more.

### Scan scope

The default scans files in the directory you name, regardless of extension, excluding `.git`; directory symlinks
are not traversed, while file symlinks are read. It checks no Git history unless you add `--git-range`. That option
checks selected commits' authors/committers, messages and added/modified blobs, not every unchanged blob.
HEAD covers commits reachable from HEAD; include other branches/tags you intend to publish. A folder package can
include untracked files and omit history; a Git push publishes committed objects reachable from the refs you share.

GREEN means no unapproved RED match under the listed rules in the material scanned. ALLOWED, NOTE and UNSCANNED
can remain. It does not mean every byte was inspected, every credential was detected, or publication is cleared.

The Linux home-prefix rule requires an ASCII A–Z/a–z account initial; a non-ASCII initial can pass unless a
configured rule catches it. A home approval covers the whole account folder portion, including other subpaths
and future occurrences in the same file, not the surrounding context. The gate does not execute source or
reconstruct values assembled at runtime; scan generated artifacts too if they will be shared.

The text assigned-secret rule requires at least 20 ASCII letters/digits/underscores/hyphens, at least three digits
and no match to its placeholder-keyword list. Short or letters-only secrets can pass. E-mail exclusions use the
exact case-insensitive `EXAMPLE_MAIL` policy: local part `noreply`, GitHub's `users.noreply.github.com`,
example-containing domains ending com/org/net, and test/invalid/example/localhost suffixes. `no-reply` is not
the same spelling; package/version and two-stand-in NOTE lists are separate.

ZIP-family containers with PK headers are opened up to three levels; members over 50 MiB are skipped. Text uses
UTF-8 replacement decoding; binaries use byte patterns, and PDF extraction tries recognized zlib/Flate stream
blocks, not every encoding or visual glyph. Reported file/member read failures and archive depth/size limits
enter UNSCANNED, but malformed ZIPs can fall back to ordinary text/bytes and failed PDF stream decodes can be
skipped without that flag. Image-file NOTEs request manual inspection; embedded images are not individually listed.
File thresholds are 50 MiB for NOTE and 100 MiB for RED unless approved. JSON lists recorded occurrences/counts.
A settling pass lists every distinct approved binary decision and its reason in the report and JSON, even if RED remains.
An ordinary run stops that rule's scan of that file at its first unapproved RED, which stays visible, so it lists only
approved decisions reached before that RED; if the file has no RED for that rule, it lists them all.

Beyond the binary listing budget of 20 per rule, repeats reached by the scan count on retained ALLOWED records;
JSON's optional `occurrences` gives that count (absent means 1), and each printed decision totals it.
NOTE keeps its 20-record binary cap.

Non-entry content of every loaded allow file is scanned, wherever it sits, and rescanned after an append. Each
file-specific ALLOWED decision reached by the scan shows its stored reason, with keys/e-mails masked; missing reasons say "not recorded".

## Why it is built this way

**The idea.** Scan the material you will actually share. A folder package can include untracked files and caches; a Git push publishes reachable committed objects for the refs you push. The default directory scan excludes `.git` and does not inspect history.

**Where it came from.** The rule set grew one incident at a time: seed data embedded in a public app template; a repo made public with its history still carrying account names and internal notes; a `.pyc` with a username that passed because the scan excluded cache directories; a stale README command; a personal address as commit author. Each of those is a self-test sample now.

**Evidence.** What was broken on purpose to show that the self-tests can fail is under [Verify](#verify); what was run end to end, and in which agent, is under [Compatibility](#compatibility).

## Install

Pick one of four ways: three for Claude Code, one for OpenAI Codex. Skills load when a session starts, so open a **new** session after installing.

### 1 · Terminal, one command

```bash
git clone https://github.com/NickkkLian/nk-publish-gate ~/.claude/skills/nk-publish-gate
```

1. Run the command above (for one project only, clone into `.claude/skills/nk-publish-gate` inside that project).
2. Start a new Claude Code session.
3. Check it loaded: type `/nk-publish-gate` — it appears in the slash-command menu. Or just ask for the task; the skill triggers on its own.

### 2 · Claude Code in a terminal session (plugin)

The plugin route goes through the [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) marketplace. Add it once; after that each skill is one command.

```
/plugin marketplace add NickkkLian/nickkk-skills
/plugin install nk-publish-gate@nickkk-skills
```

1. In a Claude Code session, run the first line (once per machine).
2. Run the second line.
3. Start a new session (or run `/reload-plugins`). The skill shows up as `nk-publish-gate:nk-publish-gate`.

Without opening a session, the same two steps work from a shell: `claude plugin marketplace add NickkkLian/nickkk-skills` then `claude plugin install nk-publish-gate@nickkk-skills`.

### 3 · Claude desktop app (Code tab)

**Add the marketplace first — Discover only searches marketplaces you have already added.**

<img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/panel-route.gif" alt="Adding the marketplace and installing a skill in the desktop app" width="640">

<sub>Recorded on 2026-09-16, when the marketplace listed ten skills, all at version 0.1.0; it lists more now. The repository list in this recording shows the recorder's own repositories because a GitHub account is connected; yours will show yours. Type the full name as in step 4.</sub>

1. In the chat box, type `/plugin marketplace` and press Enter (or open **Settings → Customize → Plugins**). The **Plugins** panel opens.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step1-type-plugin-marketplace.png" alt="/plugin marketplace typed in the chat box" width="480">
2. Top right, open **Add ▾** and choose **Add marketplace**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step2-add-menu.png" alt="The Add menu with Add marketplace" width="480">
3. Choose **Add from a repository**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step3-add-from-repository.png" alt="Add marketplace dialog: Add from a repository" width="480">
4. In **URL**, type the full `NickkkLian/nickkk-skills`. At the bottom of the list choose the row **Use "NickkkLian/nickkk-skills"**, then press **Sync**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step4-url-then-sync.png" alt="URL filled in, Sync button" width="480">
5. You land on **Discover**, filtered to the new marketplace (**Filter · 1**). Find **Nk publish gate** and press **Add**. Installed ones show **✓ Added**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step5-discover-add.png" alt="Discover list with Added and Add buttons" width="480">
6. Close the panel and start a new session.

To try it for one session without installing anything: `claude --plugin-dir ./nk-publish-gate` from a clone.

### 4 · OpenAI Codex CLI

```bash
git clone https://github.com/NickkkLian/nk-publish-gate.git ~/.agents/skills/nk-publish-gate
```

1. Run the command above (for one project only, clone into `.agents/skills/nk-publish-gate` inside that project).
2. Start a new Codex session.
3. Check it loaded, without spending a model call: `codex debug prompt-input | grep -o -- '- nk-publish-gate[a-z0-9:-]*' | sort -u` prints `- nk-publish-gate:nk-publish-gate:`. Codex adds the `nk-publish-gate:` prefix because this repository also carries a Claude Code plugin manifest. Ask for the task and the skill triggers on its own, or type `$` and pick it from the list.

## Compatibility

| Agent | Tested | What was checked |
|---|---|---|
| Claude Code (CLI 2.1.173, macOS) | yes | In a fresh project with an isolated Claude config, inside a macOS sandbox that blocked reading the tester's ~/.claude folder (settings, session history, memory), Desktop, Documents and Downloads, SSH keys and git identity, a plain request that never names the skill triggered it and it ran its bundled script. The route 2 plugin commands were also run from a shell with an isolated config: marketplace add, install, list. |
| OpenAI Codex CLI (0.154.0-alpha.6.2, gpt-5.6-sol, low reasoning, macOS) | yes | Copied into `~/.agents/skills` of a temporary home (the folder route 4 clones into), in a fresh project, without the user's Codex config. From a plain request that never names the skill, Codex read SKILL.md, ran the gate's self-test, scanned the folder with `scripts/publish_gate.py` and answered red with the three blocking hits: a key-shaped value, the .env file and a local absolute path. |
| Cursor, Gemini CLI | no | Not tested. Their documentation says both read `~/.agents/skills`, the folder route 4 clones into; Gemini CLI asks before it activates a skill. |

In this skill's Codex run, every call into the skill folder's scripts/ used that folder's absolute path. Route 4 was checked for this repository: cloned from GitHub into a temporary home's `~/.agents/skills`, it was listed by the step 3 command. This skill's frontmatter uses only name, description, license and metadata.

## Verify

```bash
python3 scripts/publish_gate.py --selftest
```

Python 3.9+ and Git on PATH; Python imports are standard-library only. On 2026-10-11 every self-test above passed, and
`breakcheck.py` from [nk-breakable-selftest](https://github.com/NickkkLian/nk-breakable-selftest) broke each script on purpose in a sandbox copy:

- `publish_gate.py`: 43 lines broken one at a time; 27 turned the self-test red without a traceback. Not covered: the self-test stayed green with L638, L768, L802, L805, L808, L937, L1777 switched off; switching off L506, L538, L566, L627, L666, L730, L877, L934, L946 crashed the script instead of failing a sample, which does not count as caught.

The unmutated control stayed green every time. Only lines that record a finding, raise, or return a failing exit code
were broken (the tool's pattern, or the hand-written list); a line number refers to the script as shipped in this version.
The caught mutations show only that these particular changes made a check fail. Surviving or crashing mutations do not count as covered. This is a limited reporting-line mutation exercise, not exhaustive coverage of detectors, encodings, credentials or privacy failures.

## Limits

- It cannot tell an invented value from a real one, or a contact address a project means to publish from a private one. On 20 public repositories, 10 of the 18 RED repository verdicts rested only on occurrences labelled false alarms by the reader: see [What RED meant on 20 real repositories](#what-red-meant-on-20-real-repositories).
- Text decoding is UTF-8 with replacement for invalid bytes; files with a NUL in their first 64 KiB and PDFs also receive byte-pattern scans. PDF stream extraction tries zlib/Flate data in recognized stream blocks, not every PDF encoding. Visual text in glyph outlines/screenshots is not read; textual metadata may match. Image files get a NOTE, not every embedded image.
- ZIP-family containers with a PK header are opened up to three levels; members over 50 MiB are skipped. Reported member read failures (including encryption), depth/size limits and unreadable files enter UNSCANNED. A malformed ZIP may fall back to text/bytes without that flag; a failed PDF stream decode is skipped.
- `.git` is excluded from the tree scan; history requires `--git-range`. Loaded allow files are scanned even outside the root or inside an otherwise excluded directory. Valid digest bodies alone are structural.
- Directory symlinks are not traversed; file symlinks are read. This is a scan of the selected surface, not an inventory of every linked location.
- The gate does not execute source code or reconstruct values assembled at runtime. Scan generated artifacts too if they will be shared; a clean scan of their source does not certify their generated values.
- It is not a secret scanner. The secret rule knows fourteen key formats (Anthropic, OpenAI, GitHub, AWS, Slack, Google, Stripe live keys, npm, GitLab, SendGrid, Twilio, Hugging Face, signed JWTs, PEM private keys); other formats can pass unless the text assignment matches the length/character/digit/placeholder limits above. Use gitleaks or trufflehog for secrets; gitleaks was not run next to this gate, so no head-to-head numbers are claimed.
- E-mail exclusions are the exact case-insensitive `EXAMPLE_MAIL` policy: a local part `noreply`, GitHub's `users.noreply.github.com`, domains containing `example` ending in com/org/net, and test/invalid/example/localhost suffixes. `no-reply` is not a synonym. Package/version and two-stand-in NOTE lists are separate.
- Size checks use binary units: files at least 50 MiB are NOTE; at least 100 MiB are RED unless approved.
- Rules are regular expressions: a name spelled differently passes.
- It does not judge whether the *existence* of a file should be public. That question is yours.

## Privacy

This skill's script runs on your computer, started by you or by the agent you use it in. It reads the files in the folder you name (with `--git-range`, also the commits in that range) and, if you made one, your config file of your own names and addresses; it prints its findings, masking keys and e-mail addresses and showing whole account folders for home paths. It writes reports or config only when asked (`--json`, `--init-config`); `--settle` or named `--approve` appends dated decisions and reasons to `.publish-gate-allow` at the scanned root, or to the chosen `--allow-file`. That default allow file is read on later runs. The script opens no network connection; what it prints is read by the agent you run it in, as part of your session with that agent. Questions: open an issue on this repository.

## License

MIT. Read a script before letting it run in your environment.
