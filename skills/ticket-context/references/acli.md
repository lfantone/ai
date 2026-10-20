# Jira through `acli` (no Atlassian MCP)

Authenticate once with `acli jira auth`.

```bash
acli jira workitem view IE-123 --fields summary,description,status
acli jira workitem search --jql "project = IE AND status = 'To Do'"
acli jira workitem edit -k IE-123 --summary "New title" --yes
```

## Create

Write the definition to a temporary file outside the repository, create, then delete the file:

```bash
acli jira workitem create --from-json /tmp/workitem.json --json
```

```json
{
  "projectKey": "IE",
  "type": "Task",
  "summary": "Short title",
  "description": { "version": 1, "type": "doc", "content": [] },
  "labels": ["optional"]
}
```

`type` is case-sensitive (`Task`, `Story`, `Bug`); `parentIssueId` makes it a sub-task, and
`--json` prints the result with the new key. The description is an ADF document (below);
`acli jira workitem create --generate-json` prints every field, custom ones included.

## Descriptions are ADF

`--description-file` leaves the description empty. Send it with `--from-json` instead:
`scripts/acli-set-description.sh IE-123 doc.adf.json` validates the document, wraps it as
`{ "description": <doc>, "issues": ["IE-123"] }`, and runs the edit.

An ADF document is `{ "version": 1, "type": "doc", "content": [...] }`. Common nodes — every
list item wraps a paragraph:

```json
{ "type": "heading", "attrs": { "level": 2 }, "content": [{ "type": "text", "text": "Acceptance criteria" }] }
{ "type": "paragraph", "content": [{ "type": "text", "text": "run " }, { "type": "text", "text": "yarn test", "marks": [{ "type": "code" }] }] }
{ "type": "bulletList", "content": [{ "type": "listItem", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "AC1 — …" }] }] }] }
{ "type": "rule" }
```

Marks: `strong`, `em`, `code`, `strike`, `underline`, `link` (with `attrs.href`).

`INVALID_INPUT` → check `version`, `type`, and `content` on the document, that every text node
has `text`, and the shape of each mark.
