---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
How do I get the SHA of the latest commit on the main branch in my local checkout, as a bare string I can put in a shell variable?
