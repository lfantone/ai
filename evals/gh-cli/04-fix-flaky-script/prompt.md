---
max_turns: 5
timeout_seconds: 240
allowed_tools: [Skill]
plugins: [../../../skills/gh-cli]
model: sonnet
runs: 3
---
This script runs inside a checkout of a GitHub repo and is flaky: sometimes $sha is empty, sometimes the README comes out garbled. Fix it and briefly say what was wrong.

```bash
#!/usr/bin/env bash
set -euo pipefail
sha=$(gh pr view 42 | grep -i 'commit' | awk '{print $2}')
readme=$(gh api "repos/{owner}/{repo}/contents/README.md?ref=$sha" | jq -r '.content' | base64 -d)
echo "$readme" | head -5
```
