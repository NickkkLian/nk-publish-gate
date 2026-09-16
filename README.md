# nk-publish-gate

A [Claude Code](https://code.claude.com) skill. Privacy and secret gate to run before anything goes public — a repo, a release zip, a demo folder, a PDF.

Part of [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) — skills that stop an AI coding agent's
"done, tested, safe" from being taken on faith.

## What it does

- Opens archives (zip/xlsx/docx/pptx) three levels deep, member names included; inflates PDF streams; scans binaries as bytes; looks at every file regardless of extension.
- `--git-range` scans every commit's author, message and blobs — a deleted secret is still in history.
- Your own identifiers live in a config outside every repo; built-in rules work without it.
- Self-test with one sample per rule and a clean control; four destructive mutations verified red.

The full procedure, the boundaries and where the rules came from are in [SKILL.md](SKILL.md).

## Install

Copy the folder into your skills directory (the skill is the repository root):

```bash
git clone https://github.com/NickkkLian/nk-publish-gate ~/.claude/skills/nk-publish-gate
```

or inside one project: `git clone … .claude/skills/nk-publish-gate`.

As a plugin, through the marketplace in the index repository:

```
/plugin marketplace add NickkkLian/nickkk-skills
/plugin install nk-publish-gate@nickkk-skills
```

To try it for one session without installing: `claude --plugin-dir ./nk-publish-gate`.

## Verify

```bash
python3 scripts/publish_gate.py --selftest
```

Standard library only, Python 3.9+. Before publishing, the guarded lines of each script were
mutated one at a time in a sandbox copy and the self-test was confirmed to go red on the named
assertion, without a traceback; the unmutated control stayed green.

## License

MIT. Read a script before letting it run in your environment.
