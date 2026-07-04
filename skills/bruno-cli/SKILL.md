---
name: bruno-cli
description: Author and run Bruno API collections via the `bru` CLI — turn verification scenarios into persistent, re-runnable .bru files with declarative assertions, execute them against an environment, and parse the JSON report deterministically. Use when verifying APIs end-to-end, building a QA collection for a ticket, or re-running API verification cheaply (locally or in CI).
---

# Bruno CLI — API verification as artifacts

[Bruno](https://usebruno.com) stores API scenarios as plain-text `.bru` files — a
collection is a folder you can commit, re-run, and hand to CI. Verified against
**`@usebruno/cli` 3.5** (run via `npx --yes @usebruno/cli` when `bru` isn't installed).

## The one rule

Scenarios live as **`.bru` artifacts with declarative assertions**; runs produce a
**JSON report parsed with `jq`**. Never parse the human table output, and never re-derive
assertions in prose — the collection is the source of truth, so a re-verification costs
one `bru run`, not a re-authoring.

## Collection scaffold

```
<collection>/
├── bruno.json              # {"version":"1","name":"<name>","type":"collection"}
├── environments/
│   └── local.bru           # vars { baseUrl: http://localhost:3000 }
└── v1-create-user.bru      # one request per scenario
```

Request file (one per scenario; `seq` orders the run):

```
meta {
  name: V1 create user
  type: http
  seq: 1
}

post {
  url: {{baseUrl}}/api/users
}

headers {
  content-type: application/json
}

body {
  {
    "name": "Ada"
  }
}

assert {
  res.status: eq 201
  res.body.name: eq Ada
}

tests {
  test("returns an id", function () {
    expect(res.getBody().id).to.be.a("string");
  });
}
```

- `assert` = declarative checks (`res.status`, `res.body.<path>`; operators like `eq`,
  `neq`, `contains`, `gt`). Prefer these; drop to a `tests` block (chai `expect`) only
  for checks assert can't express.
- Chain scenarios with `vars:post-response { userId: res.body.id }` then `{{userId}}`
  in later requests.
- Prefix a key with `~` to disable it without deleting.

## Running

```bash
bru run --env local --reporter-json report.json          # whole collection, in seq order
bru run v1-create-user.bru --env local                   # single request
bru run <folder> -r --env local                          # a folder, recursive
bru run --env local --env-var baseUrl=https://stage.example.com   # override a var
bru run --tests-only --bail                              # only asserted requests; stop on first failure
```

Exit code is non-zero when anything fails — usable as a gate directly.

## Parsing the report (verified structure)

```bash
jq '.[0].summary' report.json          # totalRequests/passed/failed, totalAssertions, totalTests…
jq '.[0].results[]
    | {req: .request.url, status: .response.status,
       asserts: [.assertionResults[]? | {lhs: .lhsExpr, status, error}],
       tests:   [.testResults[]?      | {desc: .description, status, error}]}' report.json
```

Failures carry `status: "fail"` + an `error` message — report those lines as evidence,
never the full response bodies.

## Gotchas

- **v3 runs in Safe Mode by default** — scripts/tests cannot use npm packages or the
  filesystem. Only pass `--sandbox=developer` if a test genuinely needs it.
- `bru run` must execute **inside the collection folder** (where `bruno.json` lives).
- Environment files are just `vars { … }` — no secrets in committed collections; inject
  them at run time with `--env-var key=value`.

## Using this from sub-agents

Agents spawned via the Agent tool only see what's in their spawn prompt — they do **not**
auto-load this skill. When delegating Bruno work to a sub-agent, paste the exact scaffold
and command(s) it needs from this file into its spawn prompt.
