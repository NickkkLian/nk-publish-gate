---
name: nk-publish-gate
description: "A privacy gate to run before anything goes public (a repo, a release zip, a demo folder, a PDF): it finds what is private but is not a secret, such as a home-directory path inside an xlsx, a username in a .pyc or a personal address in the commit history. Use when you are about to push to a public repository, make a private repo public, attach files to a post, or hand a bundle to someone outside. Scans every file regardless of extension, opens archives three levels deep (member names included), inflates PDF streams, scans binaries as bytes, and with --git-range scans every commit's author, message and blobs, because publishing a repo publishes its whole history. Your own identifiers come from a config kept outside every repo. For secrets it is a backstop: run a secret scanner such as gitleaks as well. Not a replacement for reading the screenshots yourself."
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); phone fiction reservations from NANPA, Ofcom and ACMA
  version: 0.1.7
---
# Publish gate

**Publishing a folder publishes every byte in it, including the ones you cannot see: archive members, PDF
streams, cache files, and every commit in the history.** This gate looks at those bytes before you push.

> **Paths.** Commands in this skill start with `${…SKILL_DIR}`: this skill's own folder, the one that contains this SKILL.md. Claude Code fills it in. If your agent shows the placeholder as written (Codex, Cursor, Gemini CLI and others), replace it with that folder's absolute path before you run the command. Left as it is, it expands to nothing and the path breaks.

## When this applies

- A `git push` to a public remote, or flipping a repository from private to public.
- A zip / xlsx / docx / pdf / image about to be attached to a post, an email, an issue.
- A demo folder handed to a client, a reviewer, a contractor.

## One-time setup (two minutes)

1. Write your identifiers into a config **outside every repository**:
   `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py --init-config ~/.config/publish-gate/gate.json`
   then fill the lists: `identifiers` (handles, mailbox names), `legal_names`, `urls` (personal sites,
   social profiles), `usernames` (login names, hostnames), `private_names` (internal project or repo
   names), `allowed_author_emails` (the noreply address you commit with), `extra_local_paths`.
2. Run the self-test once: `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py --selftest`.

Without a config the built-in rules still run (secrets, local paths, phones, e-mails, junk files), but the
report says so in its first line — your own identifiers are then **not** being checked.

## Procedure

1. Scan the tree exactly as it will be published (the clone you will push from, not your working copy):
   `python3 ${CLAUDE_SKILL_DIR}/scripts/publish_gate.py <dir> --git-range origin/main..HEAD --json gate.json`
   For a repository going public for the first time use `--git-range HEAD` (all history).
2. Read the four lists in order: **RED** (fix, or add an allow entry `RULES::GLOB::REGEX` with a reason; it must
   cover the matched text itself, see `references/config-guide.md`),
   **ALLOWED** (still printed — every allow entry is a decision someone can review), **NOTE** (images, big
   files, AI tool names inside archives, home paths with a stand-in user, package-and-version counts, stand-in e-mail addresses, `+1` numbers in area code 555: a human looks), **UNSCANNED** (anything the gate could not open —
   open it by hand or remove it).
3. The verdict is green only when RED is empty. Keep the report next to the push evidence.
4. History is dirty and must stay public? Decide with `references/history-decision.md` before rewriting.
5. After the push, clone from the public URL and scan the clone once more. The clone is what the world got.

## What it looks for that a secret scanner does not

A secret scanner (gitleaks, trufflehog) looks for credentials, and is better at it than this gate: run one as
well. This gate is mostly about what is not a credential and still should not go public:

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

It also carries a short secret rule (fourteen key formats and `api_key = <long value>`-style assignments), and with
`--git-range` it finds a secret that was committed and then deleted. That rule is a backstop, not a scanner.

## What is a note, not RED

Five kinds of finding that 0.1.6 printed as RED are NOTEs since 0.1.7. A NOTE is printed and is in `--json`, and it
does not turn the verdict red: read the NOTE list.

- **A home path whose user folder is a stand-in.** The whole folder name, up to the next path separator and with any
  spaces in it, must be one of `user`, `username`, `yourusername`, `you`, `name`, `me`, `dev`, `node`, or three dots,
  or a name in angle brackets. Any other name is RED: an invented one such as `jane`, a single letter, a first name
  and a surname. The gate cannot know who owns a name, so a real account that is called exactly `dev` or `me` is a
  NOTE too. If that is your login, put it in the config (`usernames`), which is RED wherever it appears. The list is
  `STANDIN_USERS` in the script.
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
  eleven digits follow in all. Ten digits starting 555 with no country code stay RED, and so does 555 after a real
  area code, unless it is one of the reserved 555-01xx numbers.
- **A Windows path with forward slashes** was reported by both path rules. It is now one finding, under R05. If an
  allow entry covers the R05 finding, R04 reports the path instead.

**A repeat is one line.** The same e-mail address, the same phone digits or the same user folder name is printed
once, with its count, the number of files and its first place. Only identical values are folded. The exit code and
the verdict do not change, and `--json` lists every place.

Measured on 20 public skill repositories on 2026-10-08 (the 20 most starred under 50 MB for three skill topics),
0.1.6 against 0.1.7: RED lines printed, 5,560 to 360; RED lines for the median repository, 23 to 7.5; repositories
with a RED verdict, 19 to 18. Every one of the 5,560 findings of 0.1.6 is still in the 0.1.7 `--json`, as RED or as
a NOTE (21 Windows paths are now reported by one rule instead of two). A set picked out by hand before the change,
27 home paths with a real account name and 66 key-shaped strings, is still RED in full. That set does not cover
e-mail addresses or phone numbers: for those two rules the measurement does not show that no real one became a
NOTE. Not all of what is left needs fixing either: most of the remaining e-mail addresses and phone numbers sit in
test files and examples, and the gate does not know a test file from a real one.

## Boundaries

- Text drawn as glyph outlines in a PDF, and anything inside a screenshot, are invisible to it (NOTE lists
  the images so you look). Encrypted archives are listed as UNSCANNED.
- It is not a secret scanner. The secret rule knows fourteen key formats (Anthropic, OpenAI, GitHub, AWS, Slack,
  Google, Stripe live keys, npm, GitLab, SendGrid, Twilio, Hugging Face, signed JWTs, PEM private keys); any other
  format passes unless it sits behind `api_key =`, `token =`, `secret =` or `password =`. Use gitleaks or trufflehog
  for secrets; gitleaks was not run next to this gate, so no head-to-head numbers are claimed.
- Rules are regular expressions: a name spelled differently passes.
- It does not judge whether the *existence* of a file should be public. That question is yours.

## Provenance

Own practice, 2026-07 to 2026-09. The rule set grew one incident at a time: seed data embedded in a
public app template; a repo made public with its history still carrying account names and internal notes; a
`.pyc` with a username that passed because the scan excluded cache directories; a stale README command;
a personal address as commit author. Each of those is a self-test sample now. Phone-fiction reservations
come from the official sources linked above.
