---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/tea-cli]
model: sonnet
runs: 3
---
I'm writing a spawn prompt for a sub-agent that works inside a checkout of a repo on our Gitea 1.21 server. It must list every UNRESOLVED review comment on pull request 12 as TSV rows: comment id, file path, line number, and the first 60 characters of the body on one line. Give me the exact shell snippet I should paste into the spawn prompt.
