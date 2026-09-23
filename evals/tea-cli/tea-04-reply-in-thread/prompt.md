---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/tea-cli]
model: sonnet
runs: 3
---
Inside a checkout of a repo on our Gitea 1.21 server, a reviewer left a review comment on pull request 9, on file src/db.go line 30 (comment id 5551). I want to reply INSIDE that thread, so my reply shows up grouped with their comment, without approving or requesting changes. What's the tea command? Assume the head SHA is in $SHA.
