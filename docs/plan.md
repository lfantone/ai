# Implementation planning (`/plan-orchestrator`)

Creates the artifact used by the Plan → Implement → Verify workflow. Planning has two modes:

- **Precise** (default): Opus authors exact execution contracts for Haiku/GPT-mini.
- **Fast** (`--fast`): Sonnet authors a shorter plan that may contain guided contracts,
  which implementation routes to Sonnet.

## Usage

```text
/plan-orchestrator IE-1234
/plan-orchestrator --fast IE-1234
/plan-orchestrator "add rate limiting to the login endpoint"
```

Precise is the default so existing usage remains stable. Fast mode is explicit; the command
does not add another question just to select it.

## Flow

1. Reuse fresh repository/security profiles directly, refreshing only materially stale ones.
2. Normalize the ticket with Slowpoke.
3. Pass that full brief to Dugtrio so code mapping never runs from a bare ticket id.
4. Present the understanding checkpoint. Precise mode interviews for decisions that affect
   exact execution; fast mode asks only blocking questions.
5. Author with Mew (precise) or Meowth (fast).
6. Structurally verify ids, contracts, dependencies, and file-disjoint waves with Magneton.
7. Present the complete plan for approval or revision.

There is no separate direction-approval gate. Precise mode normally has two stops: the
interview and final plan approval. Fast mode has only final approval unless a blocking question
exists. Ticket posting remains separately gated.

## Execution contracts

Every step is self-contained and declares an execution class:

- `exact`: complete preconditions and typed operations; runs on Machop/Haiku.
- `guided`: bounded instructions and a concrete target state; runs on Machoke/Sonnet.

Precise plans contain only exact contracts. Fast plans may mix both. An exact contract uses a
small operation vocabulary: `replace_exact`, `insert_before_exact`, `insert_after_exact`,
`create_file`, and `delete_exact`.

````markdown
### S3 — Add request validation

- **Execution class:** exact
- **Files:** `src/routes/users.ts`
- **Depends on:** S1
- **Allowed context:** `src/routes/users.ts:createUser`
- **Pattern:** `src/routes/projects.ts:createProject`

#### Preconditions

- The complete Before block occurs exactly once.
- `validateCreateUser` is exported by the validation module.

#### Operations

1. **replace_exact** at `createUser`

**Before:**

```ts
const user = await userService.create(req.body);
```

**After:**

```ts
const input = validateCreateUser(req.body);
const user = await userService.create(input);
```

#### Invariants

- Preserve the response shape and error middleware path.

#### Verification

- Run: `npm test -- users-route`
- Expect: exit code `0` and invalid input returns `400`.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
````

The complete Before/anchor content is the applicability check. Mew verifies it while
authoring; the executor checks it again immediately before editing. Magneton does not perform
a separate repository-anchor pass.

## Agents

| Agent     | Model  | Job                                      |
| --------- | ------ | ---------------------------------------- |
| Slowpoke  | Haiku  | Normalize requirements                   |
| Eevee     | Sonnet | Refresh repository profile when stale    |
| Growlithe | Sonnet | Refresh security profile when stale      |
| Dugtrio   | Sonnet | Map normalized requirements to live code |
| Mew       | Opus   | Author precise exact contracts           |
| Meowth    | Sonnet | Author fast exact/guided contracts       |
| Magneton  | Haiku  | Validate plan structure                  |

## Artifacts and revisions

The approved plan is saved to `<cache>/plan-<ticket>.md`. Revisions preserve stable ids,
ticked contracts, and Execution/Verification logs. Related diffs used only during authoring
are temporary and deleted after approval.

Profiles and `learnings.md` remain shared with the other orchestrators. A fresh profile is
read directly without spawning its owner.
