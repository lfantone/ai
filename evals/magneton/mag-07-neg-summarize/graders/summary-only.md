---
type: llm
focus: last_message
---
The answer is a summary of an implementation plan. All claims must hold to pass.

1. It contains about five bullets (four to six is fine) that restate the plan's goal (evict idle sessions from the in-memory session store after an idle TTL) and its acceptance criteria (eviction on next lookup with a debug log, lastSeenAt refreshed per request, sessions within the TTL untouched, default TTL of 30 minutes).
2. It does NOT contain a structural verification verdict (no per-step OK / structural error lines, no VALID or INVALID line) and does not critique the plan.
