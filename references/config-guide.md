# Config guide (gate.json) — 0.1.8

Keep the file outside every repository (default lookup: `--config`, then `$PUBLISH_GATE_CONFIG`, then
`~/.config/publish-gate/gate.json`). It contains exactly the strings you do not want published, so it must
never be published itself.

| Key | What to put in it | Matching |
|---|---|---|
| `identifiers` | handles, private mailbox local parts, account IDs | substring, case-insensitive |
| `legal_names` | full names that must not appear | whole words |
| `urls` | personal site domains, social profile paths | substring |
| `usernames` | OS login names, machine hostnames | whole words |
| `private_names` | internal project/repo names, private hosts | substring |
| `allowed_author_emails` | the only addresses commits may carry (e.g. `12345+you@users.noreply.github.com`) | exact |
| `extra_local_paths` | mount points or workspace names to treat as local paths | substring |

## Exact approvals

Each RED finding prints `settle:` followed by an entry you can copy. Copy everything after that label into
one quoted `--approve` (or `--allow`) argument; omit the label and surrounding whitespace:

```text
SHA256 RULE FILE_DIGEST VALUE_DIGEST
```

RULE is one rule ID. FILE_DIGEST hashes the exact source file identity, so brackets, spaces, quotes and other
characters need no escaping and a key-shaped filename never puts a key in the allow file. VALUE_DIGEST hashes the
complete matched value. Both use all 64 lowercase hex characters of SHA-256 (UTF-8; undecodable binary bytes
round-trip unchanged). The generated space-delimited form contains no `::` and cannot collide with either legacy
syntax. Copy the entry body as supplied; shell-quote it as one argument. For a home path the value is the whole
account folder path, not the truncated prefix the detector originally matched, a whole subpath, or its context.
It covers other subpaths and future occurrences of that account in the same file. For a size finding it is the exact
byte size. Ordinary file identities are compact ASCII JSON arrays `["file", relative_path]`; archive identities
are `["member", base_identity, [member_names...]]`, and history uses the full commit ID with the file path or
metadata role. These arrays are hashed, not stored in the allow file. Structured identities prevent a literal
filename containing `::` from impersonating a different archive member, or a short commit prefix from identifying
another commit. The report supplies a source-file hint when the displayed location needs clarification.
An approval does not extend to another member or commit. Filenames/content and all PDF streams belong to the
same source file, so the same approved value there is covered without binding to a stream number. Line numbers are not bound:
identical matched values elsewhere in that same file/location are covered, and unrelated edits do not invalidate
the decision. Another value, even one with the same visible masked prefix, stays RED. Another file needs its own
approval. No key or full e-mail value needs to be printed or typed to make the entry.

Unix folders end at `/`; a backslash is literal there. Windows folders use either path separator. If no following
separator gives a home folder's boundary, the gate keeps the remaining segment through the line/control boundary,
including spaces, rather than approving a first word that could hide a longer account. It does not guess where
trailing prose begins; such an ambiguous approval may need renewal if that trailing text changes.

Scan, show the person the findings, ask which named findings they approve, then copy each approved finding's
entry into a separate `--approve` argument:

```sh
python3 scripts/publish_gate.py folder
python3 scripts/publish_gate.py folder --approve 'ENTRY_FROM_REPORT' --reason 'public explanation'
python3 scripts/publish_gate.py folder
```

Repeated `--approve` arguments share the supplied reason, but each must name a current RED finding. Unknown
or stale entries, missing reasons and multiline reasons are refused before any append. There is no approve-all
flag. At a terminal, `--settle` shows each rule, file/line, masked finding, context and a sentence about when it
would be real; answer yes/no and give a reason for each yes. A no remains RED. A completed pass appends dated
comment/entry pairs, preserving every previous byte; EOF or an invalid answer appends nothing. A successful
partial settlement still exits 1 when RED remains; no RED means exit 0; usage/self-test errors exit 2.
Settlement scans enumerate recognized RED binary matches under these rules for this review.

A settling pass lists every distinct approved binary decision and its reason in the report and JSON, even if RED remains.
An ordinary run stops that rule's scan of that file at its first unapproved RED, which stays visible, so it lists only
approved decisions reached before that RED; if the file has no RED for that rule, it lists them all.

Beyond the binary listing budget of 20 per rule, repeats reached by the scan count on retained ALLOWED records;
JSON's optional `occurrences` gives that count (absent means 1), and each printed decision totals it.
NOTE keeps its 20-record binary cap.

The default file is `folder/.publish-gate-allow`, read automatically at the root with its entry count printed.
`--ignore-default-allow` ignores its decisions. `--allow-file F` also reads F and uses it as the append destination;
settling can create F, but an absent input file on a normal scan is a usage error (one line, exit 2). `--allow ENTRY`
also accepts a generated entry. Valid digest entry bodies in the default file or explicitly read allow files are
structural; the rest of every loaded file is scanned, including comments and legacy entries, even outside the
scanned root. It is scanned again after settling appends entries. A file already scanned in the tree is not
scanned twice. The default remains structurally
recognized when its decisions are ignored. Digest-looking lines in ordinary files receive no exemption.

Reasons must be public explanations: pasting a key into a comment in the allow file is still RED. A digest can
reveal a guessed low-entropy value, but settling says that value may be published in this file, so the value is in
the same repository anyway; an allow file must still never be where a real secret is approved.

Use `--scope-all-files` only if the person explicitly approves the same rule/value everywhere. It converts each
named approval into `SHA256-WIDE RULE * VALUE_DIGEST`, visibly WIDE in the report. This form supports all files,
not arbitrary globs; exact paths remain the default. It still cannot cover a different value or rule.

An entry that covers no finding is printed as UNUSED (including an entry shadowed by an earlier one). Keep the
ALLOWED list in the report: each file-specific decision reached by the scan shows its reason, or "not recorded" if absent. Generated
date/reason comments immediately before an entry supply the reason; arbitrary comments are still scanned but are
not inferred to be reasons. Keys and e-mail addresses in displayed/JSON reasons are masked. Settling is a reviewable
publication decision, not evidence that a credential is safe.

## Legacy regex entries

Both existing forms below retain their matching behavior. These patterns can silence a class of hits; they are
supported for existing allow files, and every legacy regex entry is reported as WIDE because it can cover more
than one complete value. Prefer generated digest entries for new decisions.

The form is `RULES::GLOB::REGEX`, for example `R10::README.md::you@example\.org`. A hit is allowed only when its
rule is in RULES (a comma list, such as `U01,U02`), its path matches GLOB, and one match of REGEX on the same line
covers the matched text itself (in a binary: within 200 bytes on either side). Every match on a line is its own
hit. An entry may cover several different values on that line or elsewhere if its regex spans each one: a prefix
entry for `alice` can cover `alicewong`, and `contact.md::.*` covers every rule in that file. No automatic narrowing
is applied to old entries.

Allow files take one entry per line. Blank lines and whole-line comments (including indented comments) are
accepted. Whitespace followed by an unescaped `#` outside character classes in the legacy regex field is refused
with an inline-comment message; hashes in filenames, escapes and character classes keep their literal behavior.
Put comments on their own lines. File paths are hashed exactly, so a `#` in a path never becomes a comment in a generated entry.
Invalid regexes are usage errors.

Changed in 0.1.2. Until 0.1.1 an entry counted when its REGEX matched anywhere within 24 characters of a hit, so an
allowed word could also let through a secret or a path right next to it. The two-field form `GLOB::REGEX` is still
read (it applies to any rule) and is judged by the new rule; add the rule IDs when you next touch the entry.

Stand-ins (0.1.7). A home path is a NOTE, not RED, and needs no allow entry, when its whole user folder name is `user`,
`username`, `yourusername`, `you`, `name`, `me`, `dev` or `node`, three dots or a name in angle brackets. So is an
e-mail address whose two sides are both on the script's two short lists (`STANDIN_MAIL_LOCAL`,
`STANDIN_MAIL_DOMAIN`), and a phone number written with `+1` and area code 555. None of these lists is read from the
config. A real account named exactly like a stand-in is a NOTE as well, so if your login is `dev` or `me`, add it to
`usernames`: a name there, or in `identifiers`, is RED wherever it appears. A package name followed by `@` and a
version number is not an e-mail address; each one is a NOTE record in `--json`, printed as one line per file.

Repeats (0.1.8). Identical matched values under the same rule in one file/location print as one RED decision;
another file prints separately. ALLOWED groups only repeats of the same file/value and matching approval and
shows each reported decision's reason; NOTE retains earlier grouping. `--json` lists recorded occurrences (subject to
ordinary binary listing limits) and includes `settle_entry`, `real_if` and masked `allow_reason` on ALLOWED records.
A forward-slash Windows path is reported under R05
only. A legacy regex allowing R05 still exposes R04 as before, so that regex needs both IDs (`R04,R05::…`). A new
exact digest approval of R05 keeps the path a single finding; no second approval is needed.

Detection change (0.1.8). R04 now recognizes an uppercase ASCII initial after the Linux home prefix as well as a
lowercase one, in text and binaries. The account is RED unless the existing stand-in policy makes it a NOTE.
This is the sole expansion of detections; no rule or tier was made quieter.

## What a GREEN scan covers

GREEN means no unapproved RED match under the listed rules in the material scanned. It can coexist with
ALLOWED, NOTE and UNSCANNED; it does not certify every byte or credential. Python 3.9+ and Git on PATH are
prerequisites: every scan runs a self-test with temporary files and Git repositories.

The default scans directory files regardless of extension, excluding `.git`; it does not scan history.
Directory symlinks are not traversed; file symlinks are read.
`--git-range` adds selected commits' author/committer metadata, messages and added/modified blobs, not every
unchanged blob. HEAD covers its reachable commits, not every repository ref. Loaded allow files are included
wherever they sit. A package and a Git push have different surfaces; choose both the directory and refs you share.

The Linux home-prefix pattern requires an ASCII A–Z/a–z account initial. Non-ASCII initials can pass without a
matching configured rule. The text assigned-secret pattern needs at least 20 ASCII letters/digits/underscores/
hyphens, at least three digits, and no `PLACEHOLDER` match; short or letters-only secrets can pass. E-mail
exclusions are the script's exact `EXAMPLE_MAIL` pattern (local part `noreply`, GitHub's users.noreply domain,
example-containing com/org/net domains and test/invalid/example/localhost suffixes), not all no-reply spellings.

Source code is scanned statically: runtime-assembled values are not reconstructed. Scan generated artifacts if
they will be published. Text uses UTF-8 replacement decoding; NUL-marked binaries and PDFs also get byte-pattern
checks. PDF extraction supports recognized zlib/Flate stream blocks, not arbitrary encodings or visual glyphs.
ZIP-family containers are opened up to three levels; members over 50 MiB are skipped. Reported file/member read
errors and archive depth/size limits enter UNSCANNED, but malformed ZIPs may fall back to text/bytes and failed
PDF stream decodes may be skipped without that flag. Files at least 50 MiB are NOTE; at least 100 MiB are RED
unless approved. Image-file NOTEs ask for manual inspection; embedded images are not individually inventoried.

Rule IDs: R04/R05 paths (a stand-in user: NOTE) · R07 secret shapes · R08 assigned secrets · R09 phones (`+1` with area code 555: NOTE) · R10 e-mails (package-and-version counts, two stand-ins: NOTE) · R12 junk ·
R13 tool names (NOTE) · R14 non-Latin text (NOTE, only with `--note-scripts`) · R15 big files · R16 images
(NOTE) · R17 commit authors · U01–U05 your config lists.
