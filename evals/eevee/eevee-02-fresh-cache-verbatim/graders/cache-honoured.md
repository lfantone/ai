---
type: llm
focus: last_message
---
The answer is the response to a request for a repository profile when `.agents/cache/repo-profile.md` already exists with `head:` equal to the current HEAD and a clean tree. All claims must hold to pass.

1. The cached profile is returned verbatim (all bullets, including the deploy note about node:22.6-alpine), possibly with a one-line note that the cache was fresh.
2. No new scouting summary is produced in place of the cached text; the answer does not add newly derived sections.
