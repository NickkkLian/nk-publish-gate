# nk-publish-gate

An agent skill for [Claude Code](https://code.claude.com) and [OpenAI Codex](https://developers.openai.com/codex). A privacy gate to run before anything goes public (a repo, a release zip, a demo folder, a PDF): it finds what is private but is not a secret, such as a home-directory path inside an xlsx, a username in a .pyc or a personal address in the commit history.

**What you get.** Two things that are private and are not secrets, so a secret scanner has no rule for them: a home-directory path in a text file inside a zip inside an xlsx, and the path a `.pyc` records for the file it was compiled from. A real run of nk-publish-gate 0.1.7 on 2026-10-09:

![nk-publish-gate: a real run. RED (4): a cache folder; a home path in a text file inside a zip inside an xlsx; a .pyc; and the home path that .pyc records for the file it was compiled from. Verdict: RED, do not publish](https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/results/nk-publish-gate.png)

It is a picture because this README has to pass the same gate, and two of the red lines quote a home path. The run as text is what the last command under [Try it](#try-it) prints.

![nk-publish-gate](https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/social/nk-publish-gate.png)

Part of [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) — skills that stop an AI coding agent's
"done, tested, safe" from being taken on faith.

## Try it

Nothing is installed and nothing under `~/.claude` changes: clone, run the self-test, run the example (it only writes inside the clone).

```bash
git clone https://github.com/NickkkLian/nk-publish-gate && cd nk-publish-gate
python3 scripts/publish_gate.py --selftest
mkdir -p demo/__pycache__ && printf 'print(1)\n' > demo/job.py
python3 -c "import io, zipfile; inner = io.BytesIO(); zipfile.ZipFile(inner, 'w').writestr('notes/todo.txt', 'export of /Users' + '/jane/Clients/acme/q3.xlsx'); zipfile.ZipFile('demo/book.xlsx', 'w').writestr('xl/embeddings/inner.zip', inner.getvalue())"
python3 -c "import py_compile; py_compile.compile('demo/job.py', cfile='demo/__pycache__/job.pyc', dfile='/Users' + '/jane/work/job.py')"
python3 scripts/publish_gate.py demo
```

The self-test prints:

```text
publish_gate selftest · 2026-10-09 00:22:49 · 239/239 passed
```

The last command prints what the picture at the top of this page shows; its last line is the one below, and its exit code is 1 (non-zero on purpose: it found something).

```text
verdict: 🔴 RED — do not publish
```

## What it does

- Finds a home-directory path, a personal mailbox or one of your own names wherever it sits: in a text file inside a zip inside an xlsx, in a PDF stream, in a `.pyc`, in a commit's author line. None of these is a credential, so a secret scanner has no rule for them.
- Opens archives (zip/xlsx/docx/pptx) three levels deep, member names included; inflates PDF streams; scans binaries as bytes; looks at every file regardless of extension.
- `--git-range` scans every commit's author, message and blobs — a line deleted last week is still in the history you publish.
- Your own identifiers live in a config outside every repo; built-in rules work without it.
- For secrets it is a backstop, not a scanner: fourteen key formats and `api_key = <long value>`-style assignments. Run gitleaks or trufflehog as well; what this gate adds is everything on this list that is not a credential.
- Allow entries name the rule they are for and must cover the matched text itself (`R10::README.md::you@example\.org`).
- Self-test with one sample per rule and per key format, and a clean control.
- A home path is a NOTE, not RED, when its whole user folder name is a stand-in word (`user`, `you`, `dev`, `node` and four more), three dots or a name in angle brackets. Any other folder name is RED, invented ones such as `jane` included. A real account named exactly like a stand-in is a NOTE too: put your own login in the config.
- Also NOTEs: a package name with an `@` and a version number (each one is in `--json`, one printed line per file), an e-mail address whose two sides are both stand-ins from two short lists, and a phone number written with `+1` and area code 555, which NANPA lists as not assignable. An `@` followed by four numbers stays RED. A Windows path with forward slashes is one finding, not two.
- The same address, the same phone digits or the same user folder is printed as one RED line with its count; `--json` lists every place.
- On 20 public skill repositories (2026-10-08) this took the RED lines printed from 5,560 to 360, and for the median repository from 23 to 7.5. Every 0.1.6 finding is still in `--json`, as RED or as a NOTE. The 28 home-path findings with a real account name and the 66 key-shaped strings picked out by hand in the first run are all still RED (the 28 print as 27, because a Windows path that two rules both reported is now counted once); e-mail addresses and phone numbers were not part of that hand-picked set.
- Phone checks include leading-zero national forms, phone-word bare 10/11-digit runs, and Chinese national mobiles (11 digits starting 13–19, including matching IDs). Bare ten-digit runs without a phone word stay clean. North American numbers followed by a full stop are caught; documented North American, UK and Australian fiction shapes are exempt, including a test number followed by a column delimiter and a valid ISO date/time. Extra fields and split real numbers stay RED.

The full procedure, the boundaries and where the rules came from are in [SKILL.md](SKILL.md).

## Next to gitleaks and trufflehog

For secrets, use a secret scanner. [gitleaks](https://github.com/gitleaks/gitleaks) and trufflehog know far more key formats than this
gate; gitleaks reads the git history, and with `--max-archive-depth` it opens nested archives too (its README, read 2026-10-01). This
gate's secret rule is a backstop (fourteen formats). What this gate is for is what a secret scanner has no rule for, because it is not a
credential and still should not go public: a home-directory path inside an xlsx or a PDF stream, a username in a `.pyc`, a personal
mailbox as commit author, and your own names and handles from a config. gitleaks was not installed or run next to this gate, so no
head-to-head result is claimed.

## How it works

1. Scan the tree exactly as it will be published (the clone you will push from, not your working copy).
2. Read the four lists in order: RED, ALLOWED, NOTE and UNSCANNED.
3. The verdict is green only when RED is empty.
4. History is dirty and must stay public? Decide with `references/history-decision.md` before rewriting.
5. After the push, clone from the public URL and scan the clone once more.

## Why it is built this way

**The idea.** Publishing a folder publishes every byte in it, including the ones you cannot see: archive members, PDF streams, cache files, and every commit in the history. This gate looks at those bytes before you push.

**Where it came from.** The rule set grew one incident at a time: seed data embedded in a public app template; a repo made public with its history still carrying account names and internal notes; a `.pyc` with a username that passed because the scan excluded cache directories; a stale README command; a personal address as commit author. Each of those is a self-test sample now.

**Evidence.** What was broken on purpose to show that the self-tests can fail is under [Verify](#verify); what was run end to end, and in which agent, is under [Compatibility](#compatibility).

## Install

Pick one of four ways: three for Claude Code, one for OpenAI Codex. Skills load when a session starts, so open a **new** session after installing.

### 1 · Terminal, one command

```bash
git clone https://github.com/NickkkLian/nk-publish-gate ~/.claude/skills/nk-publish-gate
```

1. Run the command above (for one project only, clone into `.claude/skills/nk-publish-gate` inside that project).
2. Start a new Claude Code session.
3. Check it loaded: type `/nk-publish-gate` — it appears in the slash-command menu. Or just ask for the task; the skill triggers on its own.

### 2 · Claude Code in a terminal session (plugin)

The plugin route goes through the [nickkk-skills](https://github.com/NickkkLian/nickkk-skills) marketplace. Add it once; after that each skill is one command.

```
/plugin marketplace add NickkkLian/nickkk-skills
/plugin install nk-publish-gate@nickkk-skills
```

1. In a Claude Code session, run the first line (once per machine).
2. Run the second line.
3. Start a new session (or run `/reload-plugins`). The skill shows up as `nk-publish-gate:nk-publish-gate`.

Without opening a session, the same two steps work from a shell: `claude plugin marketplace add NickkkLian/nickkk-skills` then `claude plugin install nk-publish-gate@nickkk-skills`.

### 3 · Claude desktop app (Code tab)

**Add the marketplace first — Discover only searches marketplaces you have already added.**

<img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/panel-route.gif" alt="Adding the marketplace and installing a skill in the desktop app" width="640">

<sub>Recorded on 2026-09-16, when the marketplace listed ten skills, all at version 0.1.0; it lists more now. The repository list in this recording shows the recorder's own repositories because a GitHub account is connected; yours will show yours. Type the full name as in step 4.</sub>

1. In the chat box, type `/plugin marketplace` and press Enter (or open **Settings → Customize → Plugins**). The **Plugins** panel opens.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step1-type-plugin-marketplace.png" alt="/plugin marketplace typed in the chat box" width="480">
2. Top right, open **Add ▾** and choose **Add marketplace**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step2-add-menu.png" alt="The Add menu with Add marketplace" width="480">
3. Choose **Add from a repository**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step3-add-from-repository.png" alt="Add marketplace dialog: Add from a repository" width="480">
4. In **URL**, type the full `NickkkLian/nickkk-skills`. At the bottom of the list choose the row **Use "NickkkLian/nickkk-skills"**, then press **Sync**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step4-url-then-sync.png" alt="URL filled in, Sync button" width="480">
5. You land on **Discover**, filtered to the new marketplace (**Filter · 1**). Find **Nk publish gate** and press **Add**. Installed ones show **✓ Added**.
   <br><img src="https://raw.githubusercontent.com/NickkkLian/nickkk-skills/main/gallery/panel-route/step5-discover-add.png" alt="Discover list with Added and Add buttons" width="480">
6. Close the panel and start a new session.

To try it for one session without installing anything: `claude --plugin-dir ./nk-publish-gate` from a clone.

### 4 · OpenAI Codex CLI

```bash
git clone https://github.com/NickkkLian/nk-publish-gate.git ~/.agents/skills/nk-publish-gate
```

1. Run the command above (for one project only, clone into `.agents/skills/nk-publish-gate` inside that project).
2. Start a new Codex session.
3. Check it loaded, without spending a model call: `codex debug prompt-input | grep -o -- '- nk-publish-gate[a-z0-9:-]*' | sort -u` prints `- nk-publish-gate:nk-publish-gate:`. Codex adds the `nk-publish-gate:` prefix because this repository also carries a Claude Code plugin manifest. Ask for the task and the skill triggers on its own, or type `$` and pick it from the list.

## Compatibility

| Agent | Tested | What was checked |
|---|---|---|
| Claude Code (CLI 2.1.173, macOS) | yes | In a fresh project with an isolated Claude config, inside a macOS sandbox that blocked reading the tester's ~/.claude folder (settings, session history, memory), Desktop, Documents and Downloads, SSH keys and git identity, a plain request that never names the skill triggered it and it ran its bundled script. The route 2 plugin commands were also run from a shell with an isolated config: marketplace add, install, list. |
| OpenAI Codex CLI (0.154.0-alpha.6.2, gpt-5.6-sol, low reasoning, macOS) | yes | Copied into `~/.agents/skills` of a temporary home (the folder route 4 clones into), in a fresh project, without the user's Codex config. From a plain request that never names the skill, Codex read SKILL.md, ran the gate's self-test, scanned the folder with `scripts/publish_gate.py` and answered red with the three blocking hits: a key-shaped value, the .env file and a local absolute path. |
| Cursor, Gemini CLI | no | Not tested. Their documentation says both read `~/.agents/skills`, the folder route 4 clones into; Gemini CLI asks before it activates a skill. |

In this skill's Codex run, every call into the skill folder's scripts/ used that folder's absolute path. Route 4 was checked for this repository: cloned from GitHub into a temporary home's `~/.agents/skills`, it was listed by the step 3 command. This skill's frontmatter uses only name, description, license and metadata.

## Verify

```bash
python3 scripts/publish_gate.py --selftest
```

Standard library only, Python 3.9+. On 2026-10-09 every self-test above passed, and
`breakcheck.py` from [nk-breakable-selftest](https://github.com/NickkkLian/nk-breakable-selftest) broke each script on purpose in a sandbox copy:

- `publish_gate.py`: 29 lines broken one at a time; 24 turned the self-test red without a traceback. Not covered: the self-test stayed green with L458, L543, L564 switched off; switching off L453, L606 crashed the script instead of failing a sample, which does not count as caught.

The unmutated control stayed green every time. Only lines that record a finding, raise, or return a failing exit code
were broken (the tool's pattern, or the hand-written list); a line number refers to the script as shipped in this version.
This shows those lines are covered. It does not show that nothing else can fail.

## Limits

- Text drawn as glyph outlines in a PDF, and anything inside a screenshot, are invisible to it (NOTE lists the images so you look). Encrypted archives are listed as UNSCANNED.
- It is not a secret scanner. The secret rule knows fourteen key formats (Anthropic, OpenAI, GitHub, AWS, Slack, Google, Stripe live keys, npm, GitLab, SendGrid, Twilio, Hugging Face, signed JWTs, PEM private keys); any other format passes unless it sits behind `api_key =`, `token =`, `secret =` or `password =`. Use gitleaks or trufflehog for secrets; gitleaks was not run next to this gate, so no head-to-head numbers are claimed.
- Rules are regular expressions: a name spelled differently passes.
- It does not judge whether the *existence* of a file should be public. That question is yours.

## Privacy

This skill's script runs on your computer, started by you or by the agent you use it in. It reads the files in the folder you name (with `--git-range`, also the commits in that range) and, if you made one, your config file of your own names and addresses; it prints what it finds, including the matched text, and writes a file only when you ask for one (`--json`, `--init-config`). The script opens no network connection and keeps nothing; what it prints is read by the agent you run it in, as part of your session with that agent. Questions: open an issue on this repository.

## License

MIT. Read a script before letting it run in your environment.
