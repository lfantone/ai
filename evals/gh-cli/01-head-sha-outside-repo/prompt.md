---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
I'm writing a shell script that runs from my home directory, NOT inside any git checkout. It needs the head commit SHA of pull request #42 in the GitHub repo acme/app, as a bare string in a variable. What's the exact gh command? Just give me the command and a one-line explanation.
