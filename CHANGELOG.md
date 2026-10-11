# Changelog

## 0.1.8 — 2026-10-10

- Keep every existing detector, tier and location with no allow entry. The sole detection expansion is R04's
  Linux account initial: `[a-z]` becomes `[A-Za-z]` in text and bytes. Uppercase accounts now follow the same
  RED/stand-in NOTE policy. Home paths display the whole account folder rather than the matched prefix.
- Supply `SHA256 RULE FILE_DIGEST VALUE_DIGEST` for every RED finding: full SHA-256 of the complete matched value,
  with the whole account folder path for a home path. Hash the file/location too, so a key-shaped filename cannot
  copy a key into the allow file. The space-delimited form cannot collide with either legacy syntax.
  File identities preserve archive member sequences and full commit IDs, preventing aliases in displayed paths.
  Filename/content and PDF streams share their source file identity; line or stream moves do not stale approvals.
  It covers that rule/value in that exact file/location,
  independent of line number. Mask keys and e-mail addresses in excerpts as well as matched-text fields.
- Add a terminal `--settle` pass and repeated named `--approve ENTRY --reason TEXT` flags for agents.
  Append dated reasons without rewriting existing bytes. No blanket approval flag and no separate state file.
  Settlement passes enumerate recognized RED binary matches; ordinary scans retain the first-RED-per-rule limit.
- Read root `.publish-gate-allow` by default and report the file/count; `--ignore-default-allow` skips decisions.
  Report unused entries. Accept indented comments and refuse inline comments explicitly. A missing allow input
  reports one usage-error line with exit 2. Valid digest bodies in recognized allow files are structural; comments,
  legacy entries and everything else are scanned, including a key pasted in a comment.
- Preserve both legacy regex forms, their prefix behavior and R05-to-R04 fallback. Mark every legacy regex
  entry as potentially wide; explicit `--scope-all-files` produces visible SHA256-WIDE entries for one rule/value.
  A digest approval for R05 keeps a forward-slash Windows path a single finding.
- Group RED decisions by rule, exact file/location and matched value; another file needs another decision.
  JSON lists recorded occurrences/counts and adds the generated entry and decision guidance.
- Scan non-entry content of every loaded allow file, including external files and post-append reasons.
  Retain dated reasons as metadata without changing matching; mask key/e-mail reasons in text and JSON.
  Display each file-specific ALLOWED decision reached by the scan with its reason, or "not recorded" when absent.
- A settling pass lists every distinct approved binary decision and its reason in the report and JSON, even if RED remains.
  An ordinary run stops that rule's scan of that file at its first unapproved RED, which stays visible, so it lists only
  approved decisions reached before that RED; if the file has no RED for that rule, it lists them all.
- Beyond the binary listing budget of 20 per rule, repeats reached by the scan count on retained ALLOWED records;
  JSON's optional `occurrences` gives that count (absent means 1), and each printed decision totals it.
  NOTE keeps its 20-record binary cap.
- Clarify copy-after-label instructions, partial-settlement exit codes, directory/history scope,
  detector limits and prerequisites. Construct self-test fixtures from pieces at runtime.
- Self-tests: 312/312, including the original 239 cases; settling regressions and retained feature-off evidence accompany
  the handback. Historical version numbers below refer to the releases measured at the time.

## 0.1.7 — 2026-10-09

After a run on 20 public skill repositories, where 19 came out RED with 5,560 lines and most of them named nobody.
Findings move to the NOTE list, which is printed and is in `--json` but does not turn the verdict red, and repeats
print on one line.

- A home path is a NOTE when its whole user folder name is a stand-in: `user`, `username`, `yourusername`, `you`,
  `name`, `me`, `dev`, `node`, three dots or a name in angle brackets. The name runs to the next path separator,
  spaces included. Any other name is RED, a single letter included. A real account named exactly like a stand-in is
  a NOTE too.
- A package name, an `@` and a version number is not an e-mail address. Each is a NOTE record in `--json`, printed
  as one line per file. An `@` followed by four numbers stays RED, whatever follows the fourth number; two or three
  numbers cannot be told from a version and are a NOTE.
- An e-mail address is a NOTE when the whole part before the `@` and the whole domain are both stand-ins from two
  short lists in the script. A stand-in on one side only stays RED.
- A phone number written with `+1` and area code 555 is a NOTE: NANPA lists that area code as not assignable (NPA
  Database, read 2026-10-08). A NOTE is not proof that the number belongs to nobody. Without the `+1`, or with 555
  after a real area code, it stays RED.
- A Windows path written with forward slashes is reported once, by R05, not by R04 as well. If an allow entry covers
  the R05 finding, R04 reports the path.
- The same e-mail address, the same phone digits or the same user folder name is printed as one RED line with its
  count and first place. Only identical values are folded. The exit code, the verdict and what `--json` holds for RED
  are unchanged; `--json` lists every place.
- Same 20 repositories after the change: 18 RED, 360 RED lines printed, 7.5 for the median repository (it was 23).
  Every 0.1.6 finding is in the 0.1.7 `--json` as RED or as a NOTE. A set picked out by hand in the first run, 27
  home paths with a real account name and 66 key-shaped strings, is still RED in full; e-mail addresses and phone
  numbers were not part of that set. Self-test 177 to 239 cases.

## 0.1.6 — 2026-10-08

- Add the listing icon for plugin directories (`.claude-plugin/icon.png`).
- The self-test's throwaway git repository gets its author through git's own options (`-c user.email`,
  `--author`) instead of a copy of the process environment. The rules and what the gate prints are unchanged.

## 0.1.5 — 2026-10-07

- Extend R09 with leading-zero national forms, phone-word bare 10/11-digit runs, and unconditional
  Chinese national mobile shapes (11 digits starting 13–19, matching IDs included).
- Catch separated North American numbers followed by a full stop while preserving word/decimal guards.
- Accept ACMA's exact fictional mobiles/services and geographical ranges, plus a whole test-number
  match followed by a tab or two or more spaces and a valid ISO date with optional time.
- Preserve whole-match discovery for split real numbers and extra fields; keep other bare ten-digit
  runs without phone context clean. Add phone self-test fixtures.
