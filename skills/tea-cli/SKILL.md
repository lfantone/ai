---
name: tea-cli
description: Interact with Gitea via the `tea` CLI reliably — fetch PR/issue/diff data, read files at a commit, post review comments with inline suggestions, and resolve threads. Use whenever a task reads from or writes to Gitea (pull requests, reviews, comments, issues) with `tea`. Encodes the api+jq standard and version-pinned payloads so responses parse deterministically.
---

# tea CLI — reliable Gitea access

`tea` is the Gitea CLI. Its convenience output is **lossy for machines**, so this skill
standardizes on the raw REST API + `jq`. Pinned to the target server **Gitea 1.21.11**
(field names verified against its swagger).

## The one rule

- **Structured data → `tea api <endpoint> | jq`.** Raw Gitea REST JSON is complete and
  jq-clean. Extract with `jq -r`.
- **Never parse `tea <subcommand> -o json` or `-f` output.** It is lossy — e.g.
  `tea pr ls -o json` returns `head: null`, silently dropping the SHA. Those forms are
  fine for _actions_ (`tea pr resolve`, `tea comment`) but not for reading data.
- **Diff / patch → the text endpoint**, parsed as text (hunk headers), never jq:
  `tea api repos/{owner}/{repo}/pulls/<index>.diff`
- **Avoid python/awk/sed** unless a transform genuinely can't be done in jq.
- Outside the repo dir, pass `--repo <owner>/<repo>` (or use full endpoint paths). The
  Gitea swagger lives at the server root: `tea api https://<host>/swagger.v1.json`.

## Endpoint + jq cheat-sheet

```bash
R="repos/{owner}/{repo}"

# Head SHA (change-detection, commit_id, verification)
tea api "$R/pulls/<index>" | jq -r '.head.sha'

# PR metadata in one shot
tea api "$R/pulls/<index>" \
  | jq '{n:.number, title, state, mergeable,
         base:.base.ref, head:.head.ref, sha:.head.sha,
         labels:[.labels[].name]}'

# The diff (TEXT, not JSON)
tea api "$R/pulls/<index>.diff"

# A file at a specific commit — contents are base64, must decode
tea api "$R/contents/<path>?ref=<sha>" | jq -r '.content' | base64 -d

# Review threads: list reviews, then each review's comments
tea api "$R/pulls/<index>/reviews" | jq -r '.[].id'
tea api "$R/pulls/<index>/reviews/<review_id>/comments" \
  | jq -r '.[] | select(.resolver == null)
           | [.id, .path, .position,
              (.body|gsub("\n";" ")|.[0:60])] | @tsv'
```

## Field reference (Gitea 1.21.11)

- **PR:** `.number`, `.title`, `.state`, `.mergeable`, `.base.ref`, `.head.ref`,
  `.head.sha`, `.labels[].name`.
- **Review comment (read):** `id`, `path`, `position` / `original_position` (real file
  line numbers), `resolver` (**null ⇒ unresolved**), `body`, `diff_hunk`, `user`.
- **File contents:** `.content` is **base64** — always `| base64 -d`.

## Posting a review with inline suggestions

`tea comment` and `tea pr review` cannot attach line-level suggestions; `tea pr review`
is interactive-only. Post a review via the API instead:

````bash
tea api -X POST "repos/{owner}/{repo}/pulls/<index>/reviews" -d @- <<'JSON'
{ "event": "COMMENT",
  "commit_id": "<head sha>",
  "body": "<overall summary>",
  "comments": [
    { "path": "<file>",
      "new_position": <new-file line number>,
      "body": "<comment text>\n\n```suggestion\n<replacement>\n```" }
  ] }
JSON
````

- `new_position` = **new-file line number** (Gitea field `NewLineNum`, "comment to new
  file line"). Not a diff offset — pass the actual file line.
- `event` = `"COMMENT"` leaves suggestions without approving/blocking.
- `commit_id` = head SHA, so comments anchor to the reviewed commit.
- The POST response returns the created comments with their `id`s — capture them if you
  need to resolve the threads later.
- **Multi-line caveat:** Gitea 1.21's review API anchors each comment to a _single_ line
  (`new_position`); there is no start/end range. A `suggestion` there replaces only that
  one line. Post single-line replacements inline; handle multi-line fixes another way
  (summary comment, or split into clean single-line suggestions).

## Actions

```bash
# Plain (non-inline) PR/issue comment
tea comment <index> "<body>"            # or: tea comment <index> -d @- <<'EOF' ... EOF

# Resolve a review thread by comment id
tea pr resolve <comment id>
```

Only resolve a thread when the underlying issue is actually gone — never just because a
line moved. Skip threads whose `resolver` is already set.

## Using this from sub-agents

Agents spawned via the Agent tool only see what's in their spawn prompt — they do **not**
auto-load this skill. When delegating a tea operation to a sub-agent, paste the exact
command(s) it needs from the cheat-sheet into its spawn prompt.
