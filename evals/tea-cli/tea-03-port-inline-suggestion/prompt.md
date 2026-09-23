---
max_turns: 5
timeout_seconds: 240
allowed_tools: [Skill]
plugins: [../../../skills/tea-cli]
model: sonnet
runs: 3
---
On GitHub I post a review with a multi-line inline suggestion like this, and it works:

```bash
gh api -X POST "repos/{owner}/{repo}/pulls/88/reviews" --input - <<'JSON'
{ "event": "COMMENT",
  "commit_id": "<head sha>",
  "body": "Simplify the export",
  "comments": [
    { "path": "src/index.ts",
      "start_line": 10, "start_side": "RIGHT",
      "line": 12, "side": "RIGHT",
      "body": "Collapse these three lines.\n\n```suggestion\nexport default app;\n```" }
  ] }
JSON
```

Now I need the equivalent for pull request 88 on our Gitea 1.21 server using the tea CLI, from inside the repo checkout. Give me the command and call out anything that doesn't carry over.
