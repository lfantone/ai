---
name: repo-learnings
description: Read and curate the repository's cross-ticket learnings file ($CACHE/learnings.md) — hard-won, repo-specific facts agents would otherwise get wrong (gotchas, deviation patterns, environment quirks, durable constraints). Use at the start of an orchestrated flow to inject relevant entries into spawns, and at wrap-up to distill new learnings from deviations, diagnoses, and fix rounds. Append-only memory — never regenerated, unlike the repo profile.
---

# Repo learnings — cross-ticket memory

`$CACHE` = the harness cache dir the orchestrator resolves (an existing cache wins; else `.opencode/cache` → `.claude/cache` → `.agents/cache`).

`$CACHE/learnings.md` accumulates what the flows **discovered the hard way** in
THIS repository, so ticket N's pain makes ticket N+1 cheaper. It complements the repo
profile with a different lifecycle:

- **Profile** (`repo-profile.md`) = what the repo IS. Re-derivable by scouting; Eevee
  regenerates it when stale.
- **Learnings** = what running the flows revealed. NOT re-derivable — never regenerate;
  only accumulate, update, and prune.

## Format

First line: `# Learnings — <repo>`. Then one entry **per line**, newest last:

```
- <fact an agent would get wrong otherwise> _(<ticket|general>, <date>, ×N)_
```

**Hard rules — the whole point of this file is that it stays scannable:**

- **One line, ≤ ~200 chars.** If it wraps past two physical lines, it is too long — cut it.
- **The fact only.** No evidence, no reproduction, no proof it's true. Commit SHAs, test
  names, file:line citations, and error strings are per-ticket noise — they live in the
  plan artifact, not here. Keep at most ONE anchor (a path or symbol) when the fact is
  useless without it.
- **Provenance is the tag, not the body.** The ticket id goes in `_( … )_`, never in the
  prose. `×N` is how many tickets have re-confirmed it.

The file is read whole into the orchestrator every flow and sliced into spawns — every
line you add is paid for on every future ticket. Bias toward NOT writing.

## Distill before you write

Findings arrive as ticket-shaped war stories. Strip them down to the transferable rule —
the ticket-specific evidence stays in the plan artifact. Ask: _"a year from now, on an
unrelated ticket, what one sentence would have saved an agent?"_ Write that sentence.

Before (a ticket-shaped finding — ~90 words, commit SHAs, test names, error strings):

> **2026-07-14 · PROJ-42 · Second confirmed "stale test-failure" ticket…** PROJ-42 reported
> two failing tests in `test_replay_bundles.py` … At HEAD (`b647749`) all 13 pass: fixed by
> `a1c5bea` (2026-05-26) … the error string is from pre-fix `3c3dfd0` …

After:

> `- Recorded container test failures can predate their fix — compare the fixing commit's
  date to the run date before changing code. _(PROJ-42, 2026-07-14, ×2)_`

## Admission test (apply before every write)

Write an entry ONLY if all hold:

- **Repo-specific** — not general knowledge, and not a per-ticket detail (those live in
  the plan artifact's logs).
- **An agent would get it wrong without it** — the same bar as skill content.
- **Durable** — still true next ticket: environment quirks, conventions the profile can't
  see, recurring deviation/mis-spec patterns, constraints the user stated.
- **Distilled** — passes the one-line hard rules above.

Good: `- special_tranformations.py is misspelled on purpose — don't "fix" it. _(general,
2026-07-13)_`. Bad: "S3 failed on 2026-07-05" (per-ticket event); "use parameterized
queries" (general knowledge); any entry that needs a commit SHA or test name to make sense
(that's a diagnosis, not a learning).

## Writing (orchestrators only, at wrap-up)

Agents never write here — they already return the raw material (Deviations, cause
hypotheses, environment findings, interview answers); the orchestrator distills:

1. Reread the file. **Dedupe:** if the fact already exists, bump its `×N` and refresh the
   date instead of appending a second line.
2. **Distill** each candidate to one line and run the admission test. Append the survivors.
   Create the file with its `# Learnings — <repo>` header if missing. Expect most wrap-ups
   to add zero or one line — a flow that adds three is usually smuggling in per-ticket detail.
3. **Compact, don't just append.** When the file drifts from the format (multi-line
   entries, embedded evidence, prose headers) or grows past ~40 entries, rewrite it:
   collapse each entry to its one-line fact, merge near-duplicates (sum their `×N`), and
   drop entries the repo has since invalidated (verify before dropping). This is the one
   allowed rewrite — the _facts_ are still append-only; only their phrasing is compacted.

## Reading (orchestrators, at their load/reuse phase)

Read the file if it exists (missing is fine — first run). Inject only the **relevant**
lines into each spawn: planning entries → the plan author; scenario/environment entries →
the QA designer and drivers; execution entries → bundled with the executors' conventions
excerpt; recurring finding classes → the reviewers. Never paste the whole file into every
spawn.
