---
name: gh-cli
description: Write, fix, or explain `gh` commands for GitHub — PR head SHA, diff, files at a commit, review comments, unresolved threads, inline `suggestion` reviews, replies, resolving threads, opening PRs. Use for any gh command, GitHub snippet, sub-agent prompt, or script parsing gh output; not plain git.
---

# gh CLI — reliable GitHub access

Standard: raw REST API + `jq`, like `tea-cli` for Gitea. REST **2022-11-28** (gh's default);
verified against `gh` 2.93.

## The one rule

- **Structured data → `gh api <endpoint> --jq '<filter>'`.** Pipe to standalone `jq` only for
  transforms `--jq` can't do. Never parse the human output of `gh pr view` / `gh pr list`.
- **Diff → text, never jq:** `gh pr diff <number>`.
- `{owner}/{repo}` in `gh api` paths resolves from the current git remote. Outside the repo,
  write paths literally (`repos/acme/app/...`) and add `-R <owner>/<repo>` to subcommands.

## Cheat-sheet

```bash
R="repos/{owner}/{repo}"

gh api "$R/pulls/<number>" --jq '.head.sha'                    # head SHA
gh api "$R/pulls/<number>" \
  --jq '{n:.number, title, state, base:.base.ref, head:.head.ref, sha:.head.sha}'
gh pr diff <number>                                            # diff (TEXT)
gh api -H "Accept: application/vnd.github.raw" "$R/contents/<path>?ref=<sha>"  # file at commit

# Review comments (flat; threads linked via in_reply_to_id)
gh api "$R/pulls/<number>/comments" --paginate \
  --jq '.[] | [.id, .path, .line // .original_line, (.body|gsub("\n";" ")|.[0:60])] | @tsv'

# Unresolved threads — resolution is GraphQL-only
gh api graphql -F owner='{owner}' -F repo='{repo}' -F pr=<number> -f query='
  query($owner:String!,$repo:String!,$pr:Int!){
    repository(owner:$owner,name:$repo){ pullRequest(number:$pr){
      reviewThreads(first:100){ nodes{
        id isResolved isOutdated path
        comments(first:20){ nodes{ databaseId author{login} body createdAt } } } } } } }' \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved|not)'
```

## Field gotchas

- Comment `line` is null once outdated — fall back to `original_line`. `side: RIGHT` = new
  file.
- A thread `id` is a GraphQL node id, not the REST comment id; match them via
  `comments.nodes.databaseId`. `isOutdated` does not mean the concern is gone.
- File contents default to base64 JSON — the raw media type above skips that.

## Posting a review with inline suggestions

````bash
gh api -X POST "repos/{owner}/{repo}/pulls/<number>/reviews" --input - <<'JSON'
{ "event": "COMMENT",
  "commit_id": "<head sha>",
  "body": "<overall summary>",
  "comments": [
    { "path": "<file>", "line": <new-file line>, "side": "RIGHT",
      "body": "<comment text>\n\n```suggestion\n<replacement>\n```" }
  ] }
JSON
````

- `line` is a new-file line the diff touches (`position` is deprecated).
- `event: "COMMENT"` neither approves nor blocks and requires the top-level `body`;
  `commit_id` pins the reviewed commit.
- Multi-line: add `"start_line": <first>, "start_side": "RIGHT"`; `line` stays the last line.
- The response returns created comment `id`s — keep them to resolve threads later.

## Actions

```bash
gh pr comment <number> --body-file - <<'EOF'        # PR-level comment
...
EOF
gh api -X POST "repos/{owner}/{repo}/pulls/<number>/comments/<comment_id>/replies" \
  -f body='<reply>'                                  # reply in a thread (REST id)
gh api graphql -F id='<thread node id>' -f query='
  mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){ thread{ isResolved } } }'
gh pr create --title '<title>' --body-file - [--draft] <<'EOF'   # open a PR
...
EOF
```

Resolve a thread only when the issue is actually gone — never because a line moved.

Sub-agents don't load skills: paste the exact commands they need into the spawn prompt.
