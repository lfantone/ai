---
name: bruno-cli
description: Author and run Bruno API collections with the `bru` CLI — scenarios as re-runnable .bru files with declarative asserts, run against an environment, JSON report parsed with jq. Use when verifying an API end to end, building a ticket's QA collection, or re-running API checks locally or in CI.
---

# Bruno CLI — API verification as artifacts

A collection is a folder of plain-text `.bru` files you can commit, re-run, and hand to CI.
Verified against **`@usebruno/cli` 3.5** (`npx --yes @usebruno/cli` when `bru` is missing).

## The one rule

Scenarios live as `.bru` files with declarative assertions; runs produce a JSON report
parsed with `jq`. Never parse the human table output or re-derive assertions in prose — a
re-verification is one `bru run`.

## Collection scaffold

```
<collection>/
├── bruno.json              # {"version":"1","name":"<name>","type":"collection"}
├── environments/
│   └── local.bru           # vars { baseUrl: http://localhost:3000 }
└── v1-create-user.bru      # one request per scenario
```

One request file per scenario (`seq` orders the run):

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

- `assert` covers `res.status` and `res.body.<path>` with `eq`, `neq`, `contains`, `gt`…;
  use `tests` (chai `expect`) only for what assert can't express.
- Chain with `vars:post-response { userId: res.body.id }`, then `{{userId}}`.
- Prefix a key with `~` to disable it.

## Running

```bash
bru run --env local --reporter-json report.json          # whole collection, seq order
bru run v1-create-user.bru --env local                   # one request
bru run <folder> -r --env local                          # a folder, recursive
bru run --env local --env-var baseUrl=https://stage.example.com   # override a var
bru run --tests-only --bail                              # asserted requests only; stop on first failure
```

A non-zero exit code means something failed — usable as a gate.

## Parsing the report

```bash
jq '.[0].summary' report.json
jq '.[0].results[]
    | {req: .request.url, status: .response.status,
       asserts: [.assertionResults[]? | {lhs: .lhsExpr, status, error}],
       tests:   [.testResults[]?      | {desc: .description, status, error}]}' report.json
```

Report failing lines (`status: "fail"` + `error`) as evidence, never full response bodies.

## Gotchas

- v3 runs in Safe Mode: scripts can't use npm packages or the filesystem. Pass
  `--sandbox=developer` only when a test truly needs it.
- `bru run` must execute inside the collection folder (where `bruno.json` lives).
- No secrets in committed environment files — inject them with `--env-var key=value`.
