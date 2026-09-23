---
type: llm
focus: last_message
---
Grade the shell snippet the answer proposes for Gitea 1.21. All claims must hold to pass.

1. It reads data with `tea api ... | jq`, not from `tea pr ... -o json` / `-f` output and not from `gh`.
2. It is a two-step walk: first list the PR's reviews (`pulls/12/reviews`) to get review ids, then fetch each review's comments (`pulls/12/reviews/<review_id>/comments`). Gitea has no flat "all review comments on a PR" endpoint.
3. It filters to unresolved comments by checking that `resolver` is null.
4. Each output row is TSV with the comment id, file path, a line number (`position` or `original_position`), and the body collapsed to one line and truncated to 60 characters.
