---
description: Run the gates and, when green, commit, push, and open the PR. Asks only about the commit message.
argument-hint: "[slug] [--draft]"
---

Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

Work dir: `<work root>/<slug>/`. Slug: $ARGUMENTS, else the one in the branch name, else the
newest folder in the work root. Running `/ship` is the user's yes to branch, commit, push, and
open the PR: don't ask about them. The one question is the commit message.

Verification, from `verify.md`'s latest run: a FAIL stops here (fix it with `/implement`, then
`/verify`). A missing `verify.md`, a NOT VERIFIED criterion, or a working tree that changed since
the run don't stop it: the PR opens as a draft and says why. Compare the run's tree id with this
line's output, before committing; `git diff --stat <run tree> <this tree>` lists the changes.

```bash
I=$(mktemp) && cp "$(git rev-parse --git-path index)" "$I" && GIT_INDEX_FILE=$I git add -A && GIT_INDEX_FILE=$I git write-tree; rm -f "$I"
```

1. **Branch** — on the default branch, create `<type>/<slug>-<short-name>`. Never commit to
   the default branch.
2. **Gates** — run the project's test, lint, and typecheck; on failure stop with the output.
3. **Commit** — stage only this work (`git status`, diff stat). Write the message by the repo's
   commit rules (AGENTS.md, commitlint, history), including how they reference ticket keys,
   else Conventional Commits. Show it and ask once: use it, or edit it. Then commit.
4. **Push** — `git push -u origin HEAD`. Never force-push: if the push is rejected, stop and
   report it.
5. **PR** — with the forge skill. If the branch already has one, the push updated it: report its
   URL. Otherwise create it, as a draft with `--draft` or unverified work, from the repo's PR
   template if it has one, else:

   ```markdown
   ## What

   <1–3 sentences: the change and why>

   ## How

   <1–3 bullets: approach and key decisions>

   ## How to test

   <one paragraph: setup, steps, expected result — from verify.md>

   Verified: <PASS / NOT VERIFIED per AC> on <environment>, and what changed since; or "not
   verified" and why.

   Ticket: <link>
   ```

   Report the URL.

Next: `/review`. Merging stays with the user.
