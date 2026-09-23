---
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
I'm in a checkout of a project hosted on GitLab. What's the glab command to get the head commit SHA of merge request !42 as a bare string?
