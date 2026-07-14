# AGENTS.md

Guidance for authoring the **skills** and **agents** in this repo. Skills follow the
open [Agent Skills](https://agentskills.io) format so they work across any
compatible agent. The overriding goal: **add capability while spending as few tokens
as possible.**

## Layout

```
skills/<skill-name>/SKILL.md   # one skill per dir; dir name == frontmatter `name`
agents/<agent-name>.md         # one spawnable agent definition per file
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

An agent is a single Markdown file in `agents/` — a self-contained, spawnable definition
another agent (usually a command) invokes by name. Frontmatter + a body that is the
agent's system prompt:

```markdown
---
name: Kadabra # spawnable display name (file: kadabra.md — lowercase filename)
description: What the agent produces and when to spawn it. # how the orchestrator picks it
model: haiku | sonnet | opus # pin the model deliberately — the intelligence tier is a design choice
reasoning: low | medium | high # optional thinking-effort hint (add a `# escalate to xhigh …` note where it applies)
temperature: 0.1 # optional — pin ONLY for deterministic executors/verifiers
color: "#E57373" # identity hex, unique per agent (harnesses with a TUI show it; type color shaded by tier)
tools: Bash, Read, Write # least-privilege list of what it may use
---

<the agent's role, its input contract, and the exact shape of the brief/output it returns>
```

Conventions:

- **Names are Generation I Pokémon only** (the original 151). Pick one whose flavor
  matches the role; evolution lines map nicely onto model tiers or agent families. The
  orchestrator persona in a command follows the same rule.
- **Self-contained.** A sub-agent only sees its spawn prompt — it does **not** auto-load
  skills or other agents. So an agent that uses a skill embeds the few exact commands it
  needs and cites the skill as the source of truth (don't make the caller paste them).
- **Return a compact brief, not raw dumps** — same token discipline as skills.
- **Match the model to the reasoning load, not the importance.** Pin the cheapest tier
  that does the job: deterministic extraction/matching → Haiku, judgment-based
  gathering/synthesis → Sonnet, open-ended reasoning → Opus. A task being _critical_ isn't
  a reason to over-provision — reliability comes from deterministic instructions (e.g. have
  the agent find a line with `grep -n` rather than counting by eye). Keep `tools`
  least-privilege, and set `reasoning` to match: every Haiku agent pins `reasoning: low`
  (the deterministic floor); Sonnet/Opus agents pin `reasoning` only when the role's load
  exceeds the tier's default (authors, reviewers, executors), so a pure gatherer that omits
  it is inheriting the default on purpose. Add a `# escalate to xhigh …` note where a
  larger input should bump it.
- Any output-format contract the agent must follow (e.g. a review finding template) lives
  in the agent's own body, so a command that spawns it can assemble the output as-is.

These files are only spawnable once the catalog is deployed as a project's `.agents/`
directory (see the README's Installation section), so an agent resolves to
`.agents/agents/<name>.md`; this repo is the source catalog.

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
- **Prefer spawning a defined agent** from `agents/` over inlining a persona in the
  command. Reference it by name; don't restate its instructions or override its model.
- **The orchestrator persona is the one exception.** The command body _is_ the top-level
  agent definition (e.g. Slowbro): it runs in the main conversation, so it can hard-stop
  and wait for user replies — something a spawned agent cannot do. Entries in `agents/`
  are workers that run to completion and return a brief; never move the orchestrator
  there.
- **Sub-agents don't auto-load skills or agent files.** A defined agent carries what it
  needs in its own body; if you spawn an ad-hoc sub-agent instead, paste the exact
  commands/instructions it needs into the spawn prompt.

## Validate before committing

```bash
skills-ref validate ./skills/<skill-name>   # skills
npm test                                     # catalog invariants (node --test)
```

## Writing tests

Tests live in `tests/*.test.mjs` and run on the Node built-in test runner. Two hard rules:

- **Arrange–Act–Assert.** Each test has three visible phases in order: **Arrange** the
  inputs/fixtures, **Act** to produce the result under test, **Assert** on it. Mark them
  with `// Arrange` / `// Act` / `// Assert` comments; keep all assertions in the Assert
  phase.
- **No imperative loops** (`for`, `while`, `do`) — they interleave act and assert and
  hide which case failed. For a data-driven check (e.g. "every agent's color is unique"),
  derive the data with array transforms (`map`/`flatMap`), **collect the offenders** with
  `filter`, then make one aggregate assertion that the offender list is empty:

  ```js
  // Assert — offenders collected, then a single assertion
  assert.deepEqual(
    rows.filter((row) => !isValid(row)).map((row) => row.id),
    [],
    "every row must be valid",
  );
  ```

  The empty-`deepEqual` names exactly which items broke, so one test still covers the
  whole set without a loop.

## Commit messages

All commits must follow [Conventional Commits](https://www.conventionalcommits.org):

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

- **type** — one of `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `build`, `ci`,
  `perf`, `style`, `revert`.
- **scope** (optional) — the affected area, e.g. `skills`, `agents`, `commands`, or a
  specific name like `review-orchestrator`.
- **description** — imperative mood, lowercase, no trailing period.
- **breaking changes** — append `!` after the type/scope and/or add a
  `BREAKING CHANGE:` footer.

Examples: `feat(agents): add porygon line-anchor verifier` ·
`docs: document conventional commits` · `refactor(commands)!: split reviewers into agents`.

If a body is included, it must be a bullet list of completed tasks. Short and concise. Less than 100 words in total.
