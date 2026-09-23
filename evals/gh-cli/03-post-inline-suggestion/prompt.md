---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
I'm in a checkout of a GitHub repo. Give me the gh command that posts a review on pull request 88 containing exactly one inline comment on line 12 of src/index.ts, with a GitHub suggestion that replaces that line with `export default app;`. The review must neither approve nor request changes. Assume the head SHA is in $SHA.
