---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/tea-cli]
model: sonnet
runs: 3
---
I'm inside a checkout of a repo hosted on our Gitea server (1.21). I need the head commit SHA of pull request #42 as a bare string in a shell variable. What's the exact tea command? Just the command and a one-line explanation.
