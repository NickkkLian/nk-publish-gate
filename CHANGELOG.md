# Changelog

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
