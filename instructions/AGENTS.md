# Working defaults

- Never commit, push, merge, open a PR, or post to a ticket, PR, or chat without an explicit
  yes (running `/ship` is one for its commit, push, and PR).
- Commits follow Conventional Commits unless the repo defines its own rules.
- Every behaviour change ships with unit tests. Run the project's test, lint, and typecheck
  before calling work done.
- Report failures with the real output; never claim a check you didn't run.
- Project instructions and code patterns beat these defaults.
- Raise dependencies and blockers as soon as found.
- Workflow state lives in `~/.agents/work/<repo>/<slug>/`, shared by every worktree.
- Flow: `/investigate` → `/plan` → `/implement` → `/verify` → `/ship` → `/review`.
