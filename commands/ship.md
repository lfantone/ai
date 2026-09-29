---
description: Commit, push, and open a PR for the current work — Conventional Commit, PR body linked to the ticket, each outward step confirmed.
argument-hint: "[ticket] [--draft]"
---

Ticket: $ARGUMENTS, else the slug from the branch or `.agents/work/`.

1. **Branch** — on the default branch, propose `<type>/<ticket>-<short-slug>`; create it on
   yes.
2. **Gates** — run the project's test, lint, and typecheck; on failure stop with the output.
3. **Commit** — show `git status` and the diff stat; stage only this ticket's changes. Draft a
   Conventional Commit (`type(scope): imperative lowercase summary`, body only when it adds
   why), following the repo's own rules (AGENTS.md, commitlint, history) over this default —
   including how it references ticket keys. Commit on yes.
4. **Push** — `git push -u origin HEAD` on yes.
5. **PR** — forge from `git remote get-url origin`: github.com → `gh-cli`, else `tea-cli`. Use
   the repo's PR template if it has one, else:

   ```markdown
   ## Summary

   <1–3 bullets>

   ## Ticket

   <link>

   ## Changes

   <file-level bullets>

   ## How tested

   <tests run, verification results>

   ## Acceptance criteria

   - [x] AC1 …
   ```

   Show the title and body; create on yes (draft if asked). Report the URL.

6. **Ticket** — offer the transition and a PR-link comment; only on yes.

Merging stays with the user.
