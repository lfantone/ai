---
description: Commit, push, and open a PR — what, how, and how to test. Each outward step on a yes.
argument-hint: "[slug] [--draft]"
---

Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

Work dir: `<work root>/<slug>/`. Slug: $ARGUMENTS, else the one in the branch name, else the
newest folder in the work root. If `verify.md` is missing, its latest run leaves a criterion
anything but PASS (FAIL or NOT VERIFIED), or files changed since that run's commit
(`git diff --stat <commit>`), say so, list them, and ask whether to ship anyway.

1. **Branch** — on the default branch, propose `<type>/<slug>-<short-name>`; create it on
   yes.
2. **Gates** — run the project's test, lint, and typecheck; on failure stop with the output.
3. **Commit** — show `git status` and the diff stat; stage only this work. Follow the repo's
   commit rules (AGENTS.md, commitlint, history), including how they reference ticket keys,
   else Conventional Commits. Commit on yes.
4. **Push** — `git push -u origin HEAD` on yes. If the branch already has a PR (forge skill),
   report it and stop.
5. **PR** — with the forge skill. Use the repo's PR template if it has one, else:

   ```markdown
   ## What

   <1–3 sentences: the change and why>

   ## How

   <1–3 bullets: approach and key decisions>

   ## How to test

   <one paragraph: setup, steps, expected result — from verify.md>

   Verified: <PASS / FAIL / NOT VERIFIED per AC> at <commit> on <environment>, and "shipped
   anyway" when the user chose to; or "not verified" and why.

   Ticket: <link>
   ```

   Show the title and body; create on yes (draft if asked). Report the URL.

6. **Ticket** — offer the transition and a PR-link comment; only on yes.

Next: `/review`. Merging stays with the user.
