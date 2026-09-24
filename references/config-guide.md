# Config guide (gate.json)

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

Allow entries (`--allow`, or `--allow-file` with one per line) downgrade a hit to ALLOWED; they are printed in
every report so the exception stays visible. Use them for deliberate mentions (your public e-mail on a profile
README), never to silence a class of hits.

The form is `RULES::GLOB::REGEX`, for example `R10::README.md::you@example\.org`. A hit is allowed only when its
rule is in RULES (a comma list, such as `U01,U02`), its path matches GLOB, and one match of REGEX on the same line
covers the matched text itself (in a binary: within 200 bytes on either side). Every match on a line is its own
hit, so an entry written for the first one does not cover a second.

Changed in 0.1.2. Until 0.1.1 an entry counted when its REGEX matched anywhere within 24 characters of a hit, so an
allowed word could also let through a secret or a path right next to it. The two-field form `GLOB::REGEX` is still
read (it applies to any rule) and is judged by the new rule; add the rule IDs when you next touch the entry.

Rule IDs: R04/R05 paths · R07 secret shapes · R08 assigned secrets · R09 phones · R10 e-mails · R12 junk ·
R13 tool names (NOTE) · R14 non-Latin text (NOTE, only with `--note-scripts`) · R15 big files · R16 images
(NOTE) · R17 commit authors · U01–U05 your config lists.
