# The history decision — before you make a repository public

Making a repository public exposes committed objects reachable from the refs you share; a folder package can
instead include untracked files and omit history. The default directory scan excludes `.git` and checks no
history. With Python 3.9+ and Git on PATH, run `publish_gate.py <clone> --git-range HEAD` to scan the directory
and commits reachable from HEAD. Include other branches/tags you intend to publish as well. The history scan
checks selected commits' author/committer metadata, messages and added/modified blobs, not every unchanged blob.
GREEN means no unapproved RED match under these rules in scanned material, not a complete inspection or proof
that history is safe. Use the boundaries in `config-guide.md`, then pick one row:

| Situation | Do this |
|---|---|
| History is clean and has display value (the commits show how the work grew) | publish as is |
| History is dirty, few commits, no display value | rebuild as one orphan commit, then publish |
| History is dirty, many commits that must be kept | create a new repository for the public version; the old one stays private |
| Only the commit **messages** are dirty (content clean, many commits worth keeping) | rewrite messages only (interactive rebase or filter-repo), verify with `--git-range HEAD` again |

Before any rewrite: `git bundle create before-rewrite.bundle --all` and **verify the bundle exists and
`git bundle verify` passes**. A bundle command that failed quietly is a backup that does not exist.

After the rewrite: force-push only to the branch you rewrote, then clone from the public URL and run the
gate on the clone. Forks and cached views may still hold the old objects — a secret that ever reached a
public remote must be rotated regardless.
