---
name: nk-publish-gate
description: Privacy and secret gate to run before anything goes public — a repo, a release zip, a demo folder, a PDF. Use when you are about to push to a public repository, make a private repo public, attach files to a post, or hand a bundle to someone outside. Scans every file regardless of extension, opens archives three levels deep (member names included), inflates PDF streams, scans binaries as bytes, and with --git-range scans every commit's author, message and blobs, because publishing a repo publishes its whole history. Your own identifiers come from a config kept outside every repo. Not a replacement for reading the screenshots yourself.
license: MIT
metadata:
  provenance: own practice (2026-07 to 2026-09); no external source
  version: 0.1.0
---
# Publish gate

**Publishing a folder publishes every byte in it, including the ones you cannot see: archive members, PDF
streams, cache files, and every commit in the history.** This gate looks at those bytes before you push.

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
2. Read the four lists in order: **RED** (fix, or add an `--allow 'GLOB::REGEX'` entry with a reason),
   **ALLOWED** (still printed — every allow entry is a decision someone can review), **NOTE** (images, big
   files, AI tool names inside archives: a human looks), **UNSCANNED** (anything the gate could not open —
   open it by hand or remove it).
3. The verdict is green only when RED is empty. Keep the report next to the push evidence.
4. History is dirty and must stay public? Decide with `references/history-decision.md` before rewriting.
5. After the push, clone from the public URL and scan the clone once more. The clone is what the world got.

## What it catches that a plain grep does not

- A `.pyc` in `__pycache__/` that contains the local username in a path string.
- A local path in `xl/styles.xml` inside an `.xlsx`, or inside a zip nested in that xlsx.
- A path inside a Flate-compressed PDF content stream.
- A secret that was committed, then deleted: the working tree is clean, `--git-range HEAD` is red.
- An author e-mail that is a personal mailbox rather than the noreply address.

## Boundaries

- Text drawn as glyph outlines in a PDF, and anything inside a screenshot, are invisible to it (NOTE lists
  the images so you look). Encrypted archives are listed as UNSCANNED.
- Rules are regular expressions: a name spelled differently, or a secret in an unknown format, passes.
  Add the shape to the config when you learn of one.
- It does not judge whether the *existence* of a file should be public. That question is yours.

## Provenance

Own practice, 2026-07 to 2026-09. The rule set grew one incident at a time: seed data embedded in a
public shell; a repo made public with its history still carrying account names and internal notes; a
`.pyc` with a username that passed because the scan excluded cache directories; a stale README command;
a personal address as commit author. Each of those is a self-test sample now. No external source.
