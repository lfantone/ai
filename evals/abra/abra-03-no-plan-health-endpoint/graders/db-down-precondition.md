---
type: llm
focus: last_message
---
The answer is a checklist of verification scenarios for a /health endpoint. All claims must hold to pass.

1. There is a scenario for the healthy path expecting HTTP 200 and a body with `status` equal to `ok` and a `version` field (ideally compared against package.json).
2. There is a scenario for the degraded path expecting HTTP 503 and a body with `status` equal to `degraded` and `checks.db` equal to `down`.
3. The degraded scenario has an explicit `pre:` that makes the database unreachable in a concrete way (for example stopping the `db` compose service, or pointing the api at a wrong DB host) and, if it changes shared state, says how to restore it. A degraded scenario with `pre: none` fails this claim.
4. At least one scenario asserts the response time bound (answers within 2 seconds).
