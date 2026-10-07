---
name: nk-publish-gate
description: "A privacy gate to run before anything goes public (a repo, a release zip, a demo folder, a PDF): it finds what is private but is not a secret, such as a home-directory path inside an xlsx, a username in a .pyc or a personal address in the commit history. Use when you are about to push to a public repository, make a private repo public, attach files to a post, or hand a bundle to someone outside. Scans every file regardless of extension, opens archives three levels deep (member names included), inflates PDF streams, scans binaries as bytes, and with --git-range scans every commit's author, message and blobs, because publishing a repo publishes its whole history. Your own identifiers come from a config kept outside every repo. For secrets it is a backstop: run a secret scanner such as gitleaks as well. Not a replacement for reading the screenshots yourself."
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); phone fiction reservations from NANPA, Ofcom and ACMA
  version: 0.1.5
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
   files, AI tool names inside archives: a human looks), **UNSCANNED** (anything the gate could not open —
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
