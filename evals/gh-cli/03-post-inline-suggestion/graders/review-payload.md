---
type: llm
focus: last_message
---
Grade the final answer against these claims. All must hold to pass.

1. The review is posted with `event` set to `COMMENT` (not `APPROVE` or `REQUEST_CHANGES`).
2. The payload includes a `commit_id` anchored to the head SHA (`$SHA` or equivalent).
3. The single comment's body contains a fenced block opened with ```suggestion whose content is `export default app;`.
4. The comment targets `src/index.ts` at new-file line 12.
5. The answer does not use the deprecated `position` field for addressing.
