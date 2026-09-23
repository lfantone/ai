---
max_turns: 5
timeout_seconds: 240
allowed_tools: [Skill]
plugins: [../../../skills/tea-cli]
model: sonnet
runs: 3
---
This script runs inside a checkout of a repo on our Gitea 1.21 server and is flaky: sometimes $sha is empty, and the README always comes out as gibberish. Fix it and briefly say what was wrong.

```bash
#!/usr/bin/env bash
set -euo pipefail
sha=$(tea pr ls -o json | jq -r '.[] | select(.index == 42) | .head.sha')
readme=$(tea api "repos/{owner}/{repo}/contents/README.md?ref=$sha" | jq -r '.content')
echo "$readme" | head -5
```
