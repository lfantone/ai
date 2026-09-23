---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
I'm writing a spawn prompt for a sub-agent that works inside a checkout of a GitHub repo. It must dump EVERY review comment on pull request 5 as TSV rows: comment id, file path, line number, and the first 60 characters of the body on one line. It must include comments that are outdated (their line no longer exists at head) and must not miss comments when there are more than 30. Give me the exact shell snippet I should paste into the spawn prompt.
