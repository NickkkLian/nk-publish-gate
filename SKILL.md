---
name: nk-publish-gate
description: "A local privacy check before a directory or selected Git history goes public: finds recognized patterns such as home-directory paths inside xlsx files, usernames in Python bytecode and personal addresses. Use when preparing to push to a public repository, make a private repo public or share a bundle. Scans directory files regardless of extension, excluding .git; opens supported archives up to three levels and selected PDF streams, and applies byte patterns to binaries. --git-range additionally checks selected commits' authors, committers, messages and added/modified blobs. Loaded allow-file comments are also scanned, including outside the directory. Personal identifiers come from a private config. GREEN means no unapproved RED match in scanned material, not complete inspection or publication clearance. Use a credential scanner as well and inspect images yourself."
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); phone fiction reservations from NANPA, Ofcom and ACMA
  version: 0.1.8
---
# Publish gate

Scan the material you will actually share. A folder package can include untracked files and caches; a Git push
publishes reachable committed objects for the refs you push. The default directory scan excludes `.git` and
does not inspect history. Add `--git-range` for the history you intend to publish; supported archive members,
PDF streams and binary patterns are subject to the boundaries below.

> **Paths.** Commands in this skill start with `${…SKILL_DIR}`: this skill's own folder, the one that contains this SKILL.md. Claude Code fills it in. If your agent shows the placeholder as written (Codex, Cursor, Gemini CLI and others), replace it with that folder's absolute path before you run the command. Left as it is, it expands to nothing and the path breaks.

## When this applies

- A `git push` to a public remote, or flipping a repository from private to public.
- A zip / xlsx / docx / pdf / image about to be attached to a post, an email, an issue.
- A demo folder handed to a client, a reviewer, a contractor.

## One-time setup

Prerequisites: Python 3.9+ and Git on PATH. Imports use the Python standard library, but every scan's self-test
creates temporary fixtures and invokes Git, even without `--git-range`. A successful `--selftest` output begins
with a version/date/pass-count line, then lists each check. This build was run on Python 3.13.9; other versions
were not tested here.

1. Write your identifiers into a config **outside every repository**:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py --init-config ~/.config/publish-gate/gate.json`
   then fill the lists: `identifiers` (handles, mailbox names), `legal_names`, `urls` (personal sites,
   social profiles), `usernames` (login names, hostnames), `private_names` (internal project or repo
   names), `allowed_author_emails` (the noreply address you commit with), `extra_local_paths`.
2. Run the self-test once: `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py --selftest`.

Without a config the built-in rules still run (secrets, local paths, phones, e-mails, junk files), but the
report says so on its `config:` line after the self-test banner — your own identifiers are then **not** being checked.

## Procedure

1. Scan the directory that represents the material you will share, and select the history range separately:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py <dir> --git-range origin/main..HEAD --json gate.json`
   For a repository going public for the first time, `--git-range HEAD` covers commits reachable from HEAD;
   include other branches/tags you intend to publish as well. Each selected commit's author/committer and message
   is checked, together with added/modified blobs, not every unchanged blob in every commit.
2. Read the four lists in order: **RED** (fix, or settle an intentional value after the person approves it;
   see the settling procedure below and `references/config-guide.md`),
   **ALLOWED** (each file-specific decision and its reason is printed; missing reasons say "not recorded"), **NOTE** (images, big
   files, AI tool names inside archives, home paths with a stand-in user, package-and-version counts, stand-in e-mail addresses, `+1` numbers in area code 555: a human looks), **UNSCANNED** (reported unreadable files or archive members
   skipped because of read errors or depth/size limits — open them by hand or remove them). Malformed archives
   that cannot be opened as ZIP fall back to ordinary text/bytes and are not necessarily listed as UNSCANNED.
3. GREEN means RED is empty under these rules in the material scanned. ALLOWED, NOTE and UNSCANNED can remain;
   GREEN does not mean every byte was inspected or every private value detected. Keep the report next to the push evidence.
4. History is dirty and must stay public? Decide with `references/history-decision.md` before rewriting.
5. After the push, clone from the public URL and scan the clone once more. The clone is what the world got.

## Settle a finding (0.1.8)

Every RED finding prints its rule, file and line, context, one sentence describing when it would be real,
and a `settle: SHA256 RULE FILE_DIGEST VALUE_DIGEST` line. Copy everything after `settle:` into one quoted
`--approve` argument, as below; omit the label and surrounding whitespace. No value needs typing or internal escaping.
Keys and e-mail addresses are masked; home accounts and other identifiers can be visible. Line 0 means a binary,
directory, filename or metadata finding without a text line number.
It approves exactly that rule and complete value in that file, including repeats on other lines; moving lines
does not invalidate it. A different value or a different file stays RED. Home paths print and hash the whole user
folder path, so `alice` and `alicewong` cannot share an approval. This approves the account portion, including
other subpaths and future occurrences in the same file, not the surrounding context or an entire file's content.
Open the source if two masked findings are hard to distinguish before choosing an approval.

**Agent procedure:** show the person the findings and their context, ask which named findings they approve,
and settle only the findings the person named. Do not infer consent from a test filename, an invented-looking
value, silence, or a previous approval of another file. Never approve an actual credential. Use one repeated
`--approve 'ENTRY'` for each approved finding, with `--reason 'public explanation'`:

```sh
python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py <dir> --approve 'ENTRY_FROM_REPORT' --reason 'reason the person gave'
```

For a person at a terminal, `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py <dir> --settle` walks the findings
once: yes/no for each, and a reason for each yes. A no stays RED. EOF or an invalid selection writes nothing.
The terminal pass and named-approval pass enumerate recognized RED binary matches under the implemented rules
for this review. Ordinary scans stop listing after the first unapproved RED per binary rule. In both modes,
every distinct ALLOWED decision and reason is retained in the report and JSON. Beyond the binary listing budget
of 20 per rule, repeats of an already retained ALLOWED decision are counted on a retained record instead of
creating more records; JSON's optional `occurrences` gives that count (absent means 1). NOTE retains its cap of
20 binary records per rule. JSON contains recorded occurrences/counts, not every possible byte match.
Successful partial settlement exits 1 if any RED remains; a pass with no RED exits 0. Invalid input exits 2.

Both modes append dated decisions to `<dir>/.publish-gate-allow`; they preserve existing bytes. This default file
is read on later runs, with its path and entry count printed. `--ignore-default-allow` skips its decisions.
`--allow-file F` reads an additional file and chooses it as the append destination; settling may create it.
Non-entry content of every loaded allow file is scanned, wherever it sits, and scanned again after an append.
Reasons are stored as dated comments and shown with each ALLOWED decision (keys/e-mails masked); write a public
explanation without pasting private values into it. A file already scanned in the tree is not scanned twice.

Use `--scope-all-files` only when the person explicitly approves that same rule and value in every file; those
entries and legacy regex entries are marked WIDE in the report. There is no switch to approve all findings.
Unused entries are named. Existing `RULES::GLOB::REGEX` and `GLOB::REGEX` matching behavior is preserved, including
prefix matches and class-wide patterns. Inline comments are refused; indented comments on their own line work.

The one new detection in 0.1.8 is a Linux home account starting with an uppercase ASCII letter, previously missed
by R04. It now follows the same RED/stand-in NOTE policy as a lowercase account. No existing rule was quieted.

## Personal-data patterns alongside credential scanning

Use a credential scanner such as gitleaks or trufflehog as well. This gate also checks personal-data patterns
outside usual credential rules; configurable scanners may have custom rules for them:

- A `.pyc` in `__pycache__/` that contains the local username in a path string.
- A home-directory path in `xl/styles.xml` inside an `.xlsx`, or inside a zip nested in that xlsx.
- A path inside a Flate-compressed PDF content stream.
- An author e-mail that is a personal mailbox rather than the noreply address.
- Your own identifiers from the config: handles, legal names, hostnames, private project names.
- Phone numbers and e-mail addresses that are not the officially fictional ones.

The phone rule covers international and separated North American forms (including a final full stop),
leading-zero national forms with 10–12 digits, and bare 10/11-digit runs with a phone word in the preceding
24 characters. Chinese national mobile shapes with 11 digits starting 13–19 are RED even without a phone
word, including IDs with that shape; compact and 3-4-4 groups with a single space/dash are covered. Other bare
ten-digit IDs stay clean without a phone word. Fiction exemptions are the existing North American 555-01xx
and UK 07700 900xxx / 020 7946 0xxx shapes, plus ACMA's exact Australian mobiles/services and geographical
ranges. A test number followed by a tab or two or more spaces and a valid ISO date (optionally a time) is
accepted only as that complete shape; extra number fields or real numbers split across columns stay RED.
Sources read 2026-10-07: [NANPA](https://nanpa.com/numbering/555-line-numbers),
[Ofcom](https://www.ofcom.org.uk/phones-and-broadband/phone-numbers/numbers-for-drama),
[ACMA](https://www.acma.gov.au/phone-numbers-use-tv-shows-films-and-creative-works).

It also carries fourteen key-shape patterns and an assigned-secret rule. In text, the assignment rule requires
at least 20 ASCII letters/digits/underscores/hyphens and at least three digits, with no match to `PLACEHOLDER`
(including words such as `your`, `example`, `test` and `redacted`). Short or letters-only values can pass.
`--git-range` can find matching material that was committed and later deleted within the selected history.

## What is a note, not RED

Four categories have a NOTE policy; Windows forward-slash deduplication is separate below. A recorded NOTE is
printed and is in `--json`, and it does not turn the verdict red: read the NOTE list.

- **A home path whose user folder is a stand-in.** The whole folder name, up to the next path separator and with any
  spaces in it, must be one of `user`, `username`, `yourusername`, `you`, `name`, `me`, `dev`, `node`, or three dots,
  or a name in angle brackets. Other recognized accounts are RED unless allowed: an invented one such as `jane`, a single letter, a first name
  and a surname. The gate cannot know who owns a name, so a real account that is called exactly `dev` or `me` is a
  NOTE too. If that is your login, put it in the config (`usernames`), which is RED wherever it appears. The list is
  `STANDIN_USERS` in the script. The built-in Linux home-prefix rule requires an ASCII account initial A–Z/a–z;
  a non-ASCII initial can pass unless a configured identifier/path rule catches it.
- **A package and its version.** A package name, an `@` and a version number (the form lock files are full of) has the
  shape of an e-mail address and is not one. Each is a NOTE record in `--json`; the terminal prints one line per file
  with the count. An `@` followed by four numbers (an IP address, as in a login to a machine) stays RED, whatever
  follows the fourth number. An `@` followed by two or three numbers cannot be told from a version and is a NOTE.
- **An e-mail address made of two stand-ins.** Only when the whole part before the `@` and the whole domain are each
  on a short list: the part before the `@` (`user`, `test`, `name`, `you`, `foo`, `john.doe` and a few more) and the
  domain (`company.com`, `yourdomain.com`, `acme.com`, `contoso.com`, `test.com` and a few more; no mail provider is
  on it). `STANDIN_MAIL_LOCAL` and `STANDIN_MAIL_DOMAIN` in the script are the whole lists. A stand-in on one side
  only stays RED.
- **A phone number written with `+1` and area code 555.** NANPA lists that area code as not assignable
  ([NPA Database](https://www.nanpa.com/reports/npa-reports), read 2026-10-08). The gate makes such a number a NOTE.
  That is not proof that the number belongs to nobody, so look at it. Only that exact shape: the `+1` is written and
  eleven digits total, including the country-code 1. Ten digits starting 555 with no country code stay RED, and so does 555 after a real
  area code, unless it is one of the reserved 555-01xx numbers.

**Windows forward-slash deduplication is not a NOTE downgrade.** It is one finding under R05. A legacy regex
allowing R05 exposes R04 as before and needs both IDs to cover the path. A generated exact R05 digest approval
keeps it one ALLOWED finding; no second approval is needed.

**A repeat within a file is one RED decision.** In 0.1.8 identical matched values under the same rule in the same
file/location print once with their count. The same value in another file prints separately so an approval cannot
cover an unread file. ALLOWED decisions group repeats only within the same file and matching approval, with their
stored reason; NOTE retains earlier grouping. `--json` lists each recorded occurrence and supplies
`settle_entry`, `real_if` and, for ALLOWED records, a masked `allow_reason`.

Measured on 20 public skill repositories,
0.1.6 against 0.1.7: RED lines printed, 5,560 to 360; RED lines for the median repository, 23 to 7.5; repositories
with a RED verdict, 19 to 18. Every one of the 5,560 findings of 0.1.6 is still in the 0.1.7 `--json`, as RED or as
a NOTE (21 Windows paths are now reported by one rule instead of two). A set picked out by hand before the change,
27 home-path occurrences labelled by the reader as carrying a real account name and 66 key-shaped occurrences, is still RED in full. That set does not cover
e-mail addresses or phone numbers: for those two rules the measurement does not show that no real one became a
NOTE. Not all of what is left needs fixing either: most of the remaining e-mail addresses and phone numbers sit in
test files and examples, and the gate does not know a test file from a real one.

## Boundaries

- Text decoding is UTF-8 with replacement for invalid bytes; files with a NUL in their first 64 KiB and PDFs also
  receive byte-pattern scans. PDF stream extraction tries zlib/Flate data in recognized stream blocks, not every
  PDF encoding. Visual text in glyph outlines/screenshots is not read; textual metadata may match. Image files
  get a NOTE, not every embedded image.
- ZIP-family containers with a PK header are opened up to three levels; members over 50 MiB are skipped.
  Reported member read failures (including encryption), depth/size limits and unreadable files enter UNSCANNED.
  A malformed ZIP may fall back to text/bytes without that flag; a failed PDF stream decode is skipped.
- `.git` is excluded from the tree scan; history requires `--git-range`. Loaded allow files are scanned even
  outside the root or inside an otherwise excluded directory. Valid digest bodies alone are structural.
- Directory symlinks are not traversed; file symlinks are read. This is a scan of the selected surface, not an
  inventory of every linked location.
- The gate does not execute source code or reconstruct values assembled at runtime. Scan generated artifacts
  too if they will be shared; a clean scan of their source does not certify their generated values.
- It is not a secret scanner. The secret rule knows fourteen key formats (Anthropic, OpenAI, GitHub, AWS, Slack,
  Google, Stripe live keys, npm, GitLab, SendGrid, Twilio, Hugging Face, signed JWTs, PEM private keys); other
  formats can pass unless the text assignment matches the length/character/digit/placeholder limits above. Use gitleaks or trufflehog
  for secrets; gitleaks was not run next to this gate, so no head-to-head numbers are claimed.
- E-mail exclusions are the exact case-insensitive `EXAMPLE_MAIL` policy: a local part `noreply`, GitHub's
  `users.noreply.github.com`, domains containing `example` ending in com/org/net, and test/invalid/example/localhost
  suffixes. `no-reply` is not a synonym. Package/version and two-stand-in NOTE lists are separate.
- Size checks use binary units: files at least 50 MiB are NOTE; at least 100 MiB are RED unless approved.
- Rules are regular expressions: a name spelled differently passes.
- It does not judge whether the *existence* of a file should be public. That question is yours.

## Provenance

Own practice, 2026-07 to 2026-09. The rule set grew one incident at a time: seed data embedded in a
public app template; a repo made public with its history still carrying account names and internal notes; a
`.pyc` with a username that passed because the scan excluded cache directories; a stale README command;
a personal address as commit author. Each of those is a self-test sample now. Phone-fiction reservations
come from the official sources linked above.
