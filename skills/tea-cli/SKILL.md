---
name: tea-cli
description: Write, fix, or explain `tea` commands for Gitea — PR head SHA, diff, files at a commit, reviews and unresolved comments, inline `suggestion` reviews, replies, resolving threads, opening PRs. Use for any tea command, Gitea snippet, sub-agent prompt, or script parsing tea output.
---

# tea CLI — reliable Gitea access

Standard: raw REST API + `jq`. Pinned to **Gitea 1.21.11** (fields verified against its
swagger); `tea` 0.16.

## The one rule

- **Structured data → `tea api <endpoint> | jq -r`.**
- **Never parse `tea <subcommand> -o json` or `-f`** — lossy (`tea pr ls -o json` returns
  `head: null`). Those forms are fine for actions, not reads.
- **Diff → the text endpoint**, never jq: `tea api repos/{owner}/{repo}/pulls/<index>.diff`.
- Outside the repo, pass `--repo <owner>/<repo>`. Swagger:
  `tea api https://<host>/swagger.v1.json`.

## Cheat-sheet

```bash
R="repos/{owner}/{repo}"

tea api "$R/pulls/<index>" | jq -r '.head.sha'                  # head SHA
tea api "$R/pulls/<index>" \
  | jq '{n:.number, title, state, base:.base.ref, head:.head.ref, sha:.head.sha}'
tea api "$R/pulls/<index>.diff"                                 # diff (TEXT)
tea api "$R/contents/<path>?ref=<sha>" | jq -r '.content' | base64 -d   # file at commit

# Threads: list reviews, then each review's comments; unresolved = resolver == null
tea api "$R/pulls/<index>/reviews" | jq -r '.[].id'
tea api "$R/pulls/<index>/reviews/<review_id>/comments" \
  | jq '[.[] | select(.resolver == null)
         | {id, path, line: (.position // .original_position), user: .user.login, body, diff_hunk}]'
```

## Field gotchas

- `position` / `original_position` are real file line numbers, not diff offsets.
- `resolver` null ⇒ unresolved. File `.content` is always base64.

## Posting a review with inline suggestions

`tea comment` and `tea pr review` cannot attach line suggestions (`tea pr review` is
interactive-only). Use the API:

````bash
tea api -X POST "repos/{owner}/{repo}/pulls/<index>/reviews" -d @- <<'JSON'
{ "event": "COMMENT",
  "commit_id": "<head sha>",
  "body": "<overall summary>",
  "comments": [
    { "path": "<file>", "new_position": <new-file line>,
      "body": "<comment text>\n\n```suggestion\n<replacement>\n```" }
  ] }
JSON
````

- `new_position` is the new-file line number (Gitea `NewLineNum`).
- `event: "COMMENT"` neither approves nor blocks; `commit_id` pins the reviewed commit.
- **Single line only:** 1.21 has no range, so a suggestion replaces one line. Put
  multi-line fixes in the summary or split them into single-line suggestions.
- The response returns created comment `id`s — keep them to resolve threads later.

## Replying to a thread

No reply endpoint in 1.21: post a COMMENT review with one comment at the thread's **same
`path` + `new_position`** (no `body` needed at review level) — Gitea groups it into the
thread. If that line no longer exists at head, use a PR-level `tea comment` quoting the
thread.

## Actions

```bash
tea comment <index> "$body"                          # PR-level comment (no stdin form in 0.16)
tea pr resolve <comment id>                          # resolve a thread
tea pr create --title '<title>' --description-file - [--draft] <<'EOF'   # open a PR
...
EOF
```

Resolve a thread only when the issue is actually gone — never because a line moved. Skip
threads whose `resolver` is set.

Sub-agents don't load skills: paste the exact commands they need into the spawn prompt.
