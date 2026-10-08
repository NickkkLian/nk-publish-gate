# Changelog

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
