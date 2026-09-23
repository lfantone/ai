---
type: llm
focus: last_message
---
Grade the final answer against these claims. All must hold to pass.

1. The primary command uses the GitHub GraphQL API (via `gh api graphql`) to read review threads, and filters on the thread's resolution status so that only unresolved threads are output.
2. The output includes, for each thread, the file path and the body (or a truncated body) of the first comment.
3. The answer does NOT claim that the REST review-comments endpoint (`pulls/<n>/comments`) exposes whether a thread is resolved, and does NOT try to derive resolution from REST-only fields.
4. The answer does NOT parse the human-readable output of `gh pr view` or `gh pr list` with grep/awk/sed.
