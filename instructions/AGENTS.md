# Working defaults

- Never commit, push, merge, open a PR, or post to a ticket, PR, or chat without an explicit
  yes for that action.
- Commits follow Conventional Commits unless the repo defines its own rules.
- Every behaviour change ships with unit tests. Run the project's test, lint, and typecheck
  before calling work done.
- Report failures with the real output; never claim a check you didn't run.
- The project's AGENTS.md / CLAUDE.md and existing code patterns beat these defaults.
- Raise dependencies and blockers as soon as you find them.
- Workflow state lives in `.agents/work/`, kept out of git.
- Flow: `/ticket` → `/verify` → `/ship` → `/pr-review` ⇄ `/pr-feedback`.
