# AGENTS.md

Guidance for authoring the **skills** and **agents** in this repo. Skills follow the
open [Agent Skills](https://agentskills.io) format so they work across any
compatible agent. The overriding goal: **add capability while spending as few tokens
as possible.**

## Layout

```
skills/<skill-name>/SKILL.md   # one skill per dir; dir name == frontmatter `name`
agents/<agent-name>/           # one agent per dir, with its own README.md
commands/<command-name>.md     # one invokable workflow per file
```

## Writing a skill

A skill is a directory with a `SKILL.md`: YAML frontmatter + Markdown instructions.

```markdown
---
name: pdf-processing # required. ≤64 chars, [a-z0-9-], no leading/trailing/double hyphen, == dir name
description: Extracts text and tables from PDFs and fills forms. Use when the user mentions PDFs, forms, or document extraction. # required, ≤1024 chars: what it does AND when to use it, with trigger keywords
---

<instructions>
```

Optional frontmatter: `license`, `compatibility` (≤500 chars, only if real env
requirements), `metadata` (string map), `allowed-tools` (experimental).

Optional dirs, loaded only on demand: `scripts/` (executable code), `references/`
(docs the skill reads when needed), `assets/` (templates, schemas, data).

## Token discipline (the priority)

Progressive disclosure has three tiers — respect them:

1. **`name` + `description`** (~100 tokens) — loaded for _every_ skill at startup.
   This is always-on cost, so keep descriptions tight but keyword-rich enough to
   trigger correctly. A vague description wastes activations; a bloated one taxes
   every session.
2. **`SKILL.md` body** — loaded on activation. Keep it **under 500 lines / 5000
   tokens.**
3. **`references/`, `scripts/`, `assets/`** — loaded only when the body tells the
   agent to. Push detail here.

Rules that keep token cost low:

- **Add what the agent lacks; omit what it knows.** For each line ask "would the
  agent get this wrong without it?" If no, cut it. Don't explain what a PDF or HTTP
  is — jump to the project-specific convention, API, or edge case.
- **Move detail to `references/` and gate the load.** Say _when_: "Read
  `references/api-errors.md` if the API returns a non-200." Not a generic "see
  references/". Keep reference files small and focused, one level deep.
- **Provide a default, not a menu.** Pick one tool/approach; mention alternatives in
  a clause, not as equal options.
- **Aim for moderate detail.** Concise stepwise guidance + one working example beats
  exhaustive docs. Leave rare edge cases to the agent's judgment.
- **Bundle repeated logic as a script** in `scripts/` instead of re-describing it in
  prose the agent must re-derive each run.

## Quality practices

- **Ground in real expertise, not generic advice.** Extract skills from a real task
  you completed with an agent (steps that worked, corrections you made) or synthesize
  from actual runbooks/schemas/PR comments — never from "best practices" boilerplate.
- **Calibrate control to fragility.** Be prescriptive for fragile/destructive/exact
  sequences ("run exactly this command"); give freedom (and explain _why_) where
  multiple approaches are valid.
- **Favor procedures over answers.** Teach _how to approach_ the problem class, not
  the answer to one instance, so the skill generalizes.
- **Use the high-value patterns as needed:** a `## Gotchas` section (non-obvious
  environment facts that defy assumptions — the single highest-value content),
  output-format templates, checklists for multi-step flows, and validate-then-fix
  loops for fragile work.
- **Refine with real execution.** Run the skill, read the _traces_ (not just
  outputs). Wasted steps usually mean instructions too vague, not applicable, or too
  many options. When you correct the agent, add that correction to `## Gotchas`.

## Writing an agent

Each agent lives in `agents/<name>/` with a `README.md` covering: purpose, inputs,
which skills/tools it uses, and how to run or invoke it. Prefer composing existing
skills over duplicating their instructions inline.

## Writing a command

A command is a single Markdown file in `commands/` defining an invokable workflow
(a slash command). Frontmatter plus a prompt body:

```markdown
---
description: One line — what the command does and when to run it. # shown in the command list
argument-hint: [ticket id] [PR url] # optional, documents expected arguments
---

<the workflow prompt; reference user input with `$ARGUMENTS`>
```

- Keep the same token discipline: a command that fans work out to sub-agents should
  have those agents return **compact briefs**, not raw files/diffs/tickets, and should
  never read whole files into its own context.
- **Sub-agents don't auto-load skills.** When a command spawns a sub-agent that needs a
  skill, paste the exact commands/instructions it needs into the spawn prompt.
- Compose existing skills and agents rather than inlining their logic.

## Validate before committing

```bash
skills-ref validate ./skills/<skill-name>
```
