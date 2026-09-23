---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
Get me the requirement brief for the ticket below using a sub-agent; do not read the ticket yourself. Return the sub-agent's brief verbatim and nothing else. The brief has exactly these five sections, in this order, and stays under 200 words: **Goal**, **Acceptance criteria** (bulleted), **Scope**, **Out of scope**, **Constraints**. Empty sections say _None._

There is no ticket yet; this is the description as the product owner wrote it:

We need the nightly harbor ETL to send an Apprise notification whenever a run exceeds 6 hours, including the tenant name and the elapsed time, and to write a `run-summary.json` next to the log with per-collection row counts. It must work with the existing cron entry unchanged. Not part of this: changing the retry policy or the cron schedule itself.
