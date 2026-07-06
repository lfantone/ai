---
name: repo-learnings
description: Read and curate the repository's cross-ticket learnings file (.agents/cache/learnings.md) — hard-won, repo-specific facts agents would otherwise get wrong (gotchas, deviation patterns, environment quirks, durable constraints). Use at the start of an orchestrated flow to inject relevant entries into spawns, and at wrap-up to distill new learnings from deviations, diagnoses, and fix rounds. Append-only memory — never regenerated, unlike the repo profile.
---

# Repo learnings — cross-ticket memory

`.agents/cache/learnings.md` accumulates what the flows **discovered the hard way** in
THIS repository, so ticket N's pain makes ticket N+1 cheaper. It complements the repo
profile with a different lifecycle:

- **Profile** (`repo-profile.md`) = what the repo IS. Re-derivable by scouting; Eevee
  regenerates it when stale.
- **Learnings** = what running the flows revealed. NOT re-derivable — never regenerate;
  only accumulate, update, and prune.

## Format

First line: `# Learnings — <repo>`. Then one entry per line, newest last:

```
- <fact an agent would get wrong otherwise> _(source: <flow>, <date>, seen ×N)_
```

## Admission test (apply before every write)

Write an entry ONLY if all hold:

- **Repo-specific** — not general knowledge, and not a per-ticket detail (those live in
  the plan artifact's logs).
- **An agent would get it wrong without it** — the same bar as skill content.
- **Durable** — still true next ticket: environment quirks, conventions the profile can't
  see, recurring deviation/mis-spec patterns, constraints the user stated.

Good: `- anchors under src/generated/ drift every build — plan steps must target the
templates, not the output`. Bad: "S3 failed on 2026-07-05" (per-ticket); "use
parameterized queries" (general knowledge).

## Writing (orchestrators only, at wrap-up)

Agents never write here — they already return the raw material (Deviations, cause
hypotheses, environment findings, interview answers); the orchestrator distills:

1. Reread the file. **Dedupe:** if the fact already exists, bump its `seen ×N` and date
   instead of appending.
2. Append the new one-liners that pass the admission test. Create the file with its
   header if missing.
3. **Prune** past ~40 entries: merge near-duplicates, drop entries the repo has since
   invalidated (verify before dropping), prefer keeping the highest `×N`.

## Reading (orchestrators, at their load/reuse phase)

Read the file if it exists (missing is fine — first run). Inject only the **relevant**
lines into each spawn: planning entries → the plan author; scenario/environment entries →
the QA designer and drivers; execution entries → bundled with the executors' conventions
excerpt; recurring finding classes → the reviewers. Never paste the whole file into every
spawn.
