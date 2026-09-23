---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
I'm in a checkout of a GitHub repo. List only the UNRESOLVED review threads on pull request 17, showing the file path and the body of the first comment for each thread. Give me the gh command(s) to do it.
