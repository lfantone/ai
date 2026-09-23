---
type: llm
focus: last_message
---
The answer is the response to a request for a repository profile when `.agents/cache/repo-profile.md` existed but was stale: its `head:` was all zeros (HEAD has moved) and it described jest/npm while the tree now uses vitest/pnpm. All claims must hold to pass.

1. The stale text ("jest", "Node 18", node:18.20-alpine) is NOT returned as the profile; a re-scouted brief is returned instead. Mentioning the old text to explain what was corrected is fine.
2. The new brief reflects the current tree: vitest, pnpm, the injected Clock rule, tests under `__tests__/`.
