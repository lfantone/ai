---
name: ticket-context
description: Turn a Jira key, a GitHub or Gitea issue, or a pasted Slack/Teams thread into a compact brief — goal, explicit acceptance criteria, scope, links, dependencies, open questions. Use when starting work on a ticket or asked what a ticket requires.
---

# Ticket context

## Fetch

- **Jira key** (`[A-Z][A-Z0-9]+-[0-9]+`): Atlassian MCP `getJiraIssue` with
  `responseContentFormat: "markdown"` and
  `fields: ["summary","description","status","issuetype","labels","comment","issuelinks","parent","subtasks"]`;
  `getJiraIssueRemoteIssueLinks` for linked PRs and docs; `getConfluencePage` only for a
  linked spec.
- **GitHub issue:** `gh api repos/<owner>/<repo>/issues/<n> --jq '{title,body}'`, then
  `.../comments`.
- **Gitea issue:** `tea api repos/<owner>/<repo>/issues/<n> | jq '{title,body}'`, then
  `.../comments`.
- **Slack / Teams thread:** the pasted text. Never invent a ticket around it.
- No tool access → ask for pasted text; never guess requirements.

## Brief (≤200 words)

- **Goal** — why the change exists.
- **Acceptance criteria** — `AC1…`, compressed from the explicit "acceptance criteria" /
  "done when" list. Derive from prose only when no such list exists, and say so.
- **Scope / Out of scope.**
- **Links** — PRs, docs, designs, related tickets.
- **Dependencies** — blocking tickets, other teams or services, migrations, flags,
  environment config or secrets, API contracts.
- **Open questions** — only ambiguities that change the implementation.

## Gotchas

- Jira calls need `cloudId` (UUID or site URL). If unknown, call
  `getAccessibleAtlassianResources` once.
- `getJiraIssue` omits comments and links unless requested in `fields`, and decisions often
  live in the comments.
- Background, analysis, and design-rationale sections are not criteria. Keep at most one
  line from them, under Scope, when they bound the work.
- A thin ticket: read the parent or epic before asking the user.
- In a chat thread the latest agreed message wins over earlier ones. Note who agreed.
