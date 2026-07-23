---
name: gh-cli
description: Interact with GitHub via the `gh` CLI reliably — fetch PR/issue/diff data, read files at a commit, post review comments with inline suggestions, and resolve threads. Use whenever a task reads from or writes to GitHub (pull requests, reviews, comments, issues) with `gh`. Encodes the api+jq standard and the GraphQL-only operations so responses parse deterministically.
---

# gh CLI — reliable GitHub access

`gh` is the GitHub CLI. Its human-readable output is for humans, so this skill
standardizes on the raw REST API + `jq` (same standard as the `tea-cli` skill for Gitea).
Pinned to REST API version **2022-11-28** (gh's default). Verified against `gh` 2.93.

## The one rule

- **Structured data → `gh api <endpoint> --jq '<filter>'`.** Raw GitHub REST JSON is
  complete and jq-clean. `gh api` has jq built in (`--jq`); pipe to standalone `jq` only
  for transforms `--jq` can't do.
- **Never parse the human output** of `gh pr view` / `gh pr list` etc. (`--json` with
  explicit fields is acceptable for _actions'_ prechecks, but standardize reads on
  `gh api` for complete objects).
- **Diff / patch → text, never jq:** `gh pr diff <number>` (or the api with the diff
  media type: `gh api -H "Accept: application/vnd.github.diff" repos/{owner}/{repo}/pulls/<number>`).
- **Avoid python/awk/sed** unless a transform genuinely can't be done in jq.
- `{owner}/{repo}` placeholders in `gh api` paths auto-resolve from the current repo's
  git remote. Outside the repo dir, write them literally (`repos/acme/app/...`) and add
  `-R <owner>/<repo>` to `gh` subcommands like `pr diff`/`pr comment`.

## Endpoint + jq cheat-sheet

```bash
R="repos/{owner}/{repo}"

# Head SHA (change-detection, commit_id, verification)
gh api "$R/pulls/<number>" --jq '.head.sha'

# PR metadata in one shot
gh api "$R/pulls/<number>" \
  --jq '{n:.number, title, state, mergeable,
         base:.base.ref, head:.head.ref, sha:.head.sha,
         labels:[.labels[].name]}'

# The diff (TEXT, not JSON)
gh pr diff <number>

# A file at a specific commit — use the raw media type (no base64 dance)
gh api -H "Accept: application/vnd.github.raw" "$R/contents/<path>?ref=<sha>"

# All review comments on a PR (flat; threads linked via in_reply_to_id)
gh api "$R/pulls/<number>/comments" --paginate \
  --jq '.[] | [.id, .path, .line // .original_line,
               (.body|gsub("\n";" ")|.[0:60])] | @tsv'

# Thread RESOLUTION is GraphQL-only (REST has no isResolved) — list unresolved threads:
gh api graphql -F owner='{owner}' -F repo='{repo}' -F pr=<number> -f query='
  query($owner:String!,$repo:String!,$pr:Int!){
    repository(owner:$owner,name:$repo){ pullRequest(number:$pr){
      reviewThreads(first:100){ nodes{
        id isResolved path
        comments(first:1){ nodes{ databaseId body } } } } } } }' \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
        | select(.isResolved|not)'
```

## Field reference (REST 2022-11-28)

- **PR:** `.number`, `.title`, `.state`, `.mergeable`, `.base.ref`, `.head.ref`,
  `.head.sha`, `.labels[].name`.
- **Review comment (read):** `id` (REST/database id), `path`, `line` / `original_line`
  (real new-file line numbers; `line` is null when the comment is outdated — fall back to
  `original_line`), `side` (`RIGHT` = new file), `in_reply_to_id` (thread linkage),
  `body`, `diff_hunk`, `user.login`.
- **Resolution status lives only in GraphQL** (`reviewThreads.nodes.isResolved`, thread
  `id` is a GraphQL node id — not the REST comment id; match threads to REST comments via
  `comments.nodes.databaseId`).
- **File contents:** default JSON wraps content in base64 — skip it with
  `Accept: application/vnd.github.raw`.

## Posting a review with inline suggestions

Post one review via the API (mirrors the `tea-cli` payload, with GitHub's `line`/`side`
addressing — `position` is deprecated):

````bash
gh api -X POST "repos/{owner}/{repo}/pulls/<number>/reviews" --input - <<'JSON'
{ "event": "COMMENT",
  "commit_id": "<head sha>",
  "body": "<overall summary>",
  "comments": [
    { "path": "<file>",
      "line": <new-file line number>,
      "side": "RIGHT",
      "body": "<comment text>\n\n```suggestion\n<replacement>\n```" }
  ] }
JSON
````

- `line` = **new-file line number** on `side: "RIGHT"`. Must be a line the diff touches.
- `event` = `"COMMENT"` leaves suggestions without approving/blocking.
- `commit_id` = head SHA, so comments anchor to the reviewed commit.
- **Multi-line suggestions ARE supported** (unlike Gitea 1.21): add
  `"start_line": <first line>, "start_side": "RIGHT"` and keep `line` as the last line;
  the `suggestion` block then replaces the whole range.
- The POST response returns the created comments with their `id`s — capture them if you
  need to resolve the threads later.

## Actions

```bash
# Plain (non-inline) PR comment
gh pr comment <number> --body "<body>"    # or: --body-file - <<'EOF' ... EOF

# Reply INSIDE a review thread — the dedicated replies endpoint (REST id, not node id)
gh api -X POST "repos/{owner}/{repo}/pulls/<number>/comments/<comment_id>/replies" \
  -f body='<reply text>'

# Resolve a review thread — GraphQL only, needs the thread's GraphQL id
gh api graphql -F id='<thread node id>' -f query='
  mutation($id:ID!){ resolveReviewThread(input:{threadId:$id}){
    thread{ isResolved } } }'
```

Only resolve a thread when the underlying issue is actually gone — never just because a
line moved. Skip threads already `isResolved: true`.

## Using this from sub-agents

Sub-agents don't auto-load this skill — paste the exact command(s) they need from the
cheat-sheet into their spawn prompt.
