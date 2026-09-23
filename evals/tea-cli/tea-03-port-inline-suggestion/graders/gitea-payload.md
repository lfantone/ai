---
type: llm
focus: last_message
---
The user showed a working GitHub payload and asked for the Gitea 1.21 equivalent via the tea CLI. Grade ONLY the Gitea command/payload the answer proposes (ignore the quoted GitHub original). All claims must hold to pass.

1. The Gitea review is posted with `tea api -X POST` to the `pulls/88/reviews` endpoint (not with `tea pr review`, which is interactive-only, and not with `tea comment`, which cannot attach inline suggestions).
2. Each inline comment addresses the line with `new_position` set to a new-file line number. The Gitea payload does NOT contain GitHub's `line`, `side`, `start_line`, or `start_side` fields.
3. The answer explicitly states that Gitea 1.21 anchors each review comment to a single line, so a multi-line suggestion range does not carry over, and it proposes a workaround: split into single-line suggestions, or put the multi-line replacement in the review body / a summary comment.
4. The payload keeps `event: "COMMENT"` and a `commit_id` set to the head SHA.
