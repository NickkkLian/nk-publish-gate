# The history decision — before you make a repository public

Making a repository public publishes every commit that is reachable, not the current tree. Run
`publish_gate.py <clone> --git-range HEAD` first, then pick one row:

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
