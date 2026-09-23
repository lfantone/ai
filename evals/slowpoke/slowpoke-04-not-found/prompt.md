---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Agent]
model: sonnet
runs: 5
---
Get me the requirement brief for the ticket below using a sub-agent; do not read the ticket yourself. Return the sub-agent's brief verbatim and nothing else. The brief has exactly these five sections, in this order, and stays under 200 words: **Goal**, **Acceptance criteria** (bulleted), **Scope**, **Out of scope**, **Constraints**. Empty sections say _None._

Ticket: HB-9999
