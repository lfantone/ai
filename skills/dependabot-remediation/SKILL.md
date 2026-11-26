---
name: dependabot-remediation
description: Fix open Dependabot alerts in a JS/TS repo — triage, upgrade in-range, refresh stale lockfile transitives, dismiss unpatchable dev-only alerts, assess majors, verify against baseline. Use for Dependabot/security alerts, vulnerable dependencies, npm audit, or bulk dependency upgrades.
---

# Dependabot remediation

Commands use Yarn 4 (Berry); map to npm (`npm ls`, `npm update`) or pnpm (`pnpm why`,
`pnpm update`) when the lockfile says so. GitHub access per the `gh-cli` skill.

## 1. Baseline + alerts

Run typecheck/lint/test/build on the clean tree first and save the results — later failures are
only regressions if they're new.

```bash
gh api "repos/{owner}/{repo}/dependabot/alerts" --paginate -q '.[] | select(.state=="open")
  | [.number, .security_advisory.severity, .dependency.package.name, .dependency.manifest_path,
     .dependency.scope, .security_vulnerability.vulnerable_version_range,
     (.security_vulnerability.first_patched_version.identifier // "NONE")] | @tsv'
```

## 2. Analyse each package

- Who pulls it in: `yarn why <pkg>`; direct vs transitive.
- Dev vs runtime: verify in `package.json` — the alert `scope` is often wrong.
- Target: `first_patched_version`; `NONE` → step 6.

## 3. Upgrade in-range

```bash
yarn dlx -q npm-check-updates --workspaces --root --target minor -u
yarn install
```

## 4. Refresh stale transitives

```bash
yarn up -R <pkg> [<pkg>...]
```

- A parent can stay locked old via another descriptor (e.g. `@azure/identity@^4.13.0` stuck on
  4.13.3, holding `@azure/msal-node` 6) → `yarn up -R <parent>` too.
- Then pin each transitive alert package to `^<first_patched>` so a lock regen can't drop it
  back. Root `package.json` only (workspaces ignore member overrides):
  - Yarn (1 and Berry), Bun: `"resolutions": { "<pkg>": "^1.2.3" }`
  - npm ≥ 8.3: `"overrides": { "<pkg>": "^1.2.3" }`; a direct dep must match its own spec or use
    `"$<pkg>"`
  - pnpm: `"pnpm": { "overrides": { "<pkg>@<1.2.3": "^1.2.3" } }`; pnpm 10 workspaces put
    `overrides:` in `pnpm-workspace.yaml`
- Re-run install after pinning. If the tree holds several majors of the package, scope the pin
  (Berry `"<pkg>@npm:^1"`, pnpm `"<pkg>@^1"`, npm nested `{ "<parent>": { "<pkg>": … } }`) —
  a bare pin forces one major on every consumer.

## 5. Re-verify

`yarn why <pkg>` for every alert package; loop 3–4 until every resolved version is
`>= first_patched_version`.

## 6. No patched version

Assess impact: who uses it, dev-only tooling vs shipped runtime. Runtime → report, don't
dismiss. Dev-only → **ask the user**, then:

```bash
gh api -X PATCH "repos/{owner}/{repo}/dependabot/alerts/<n>" -f state=dismissed \
  -f dismissed_reason=tolerable_risk -f dismissed_comment="<dev-only: who uses it, why safe>"
```

## 7. Majors

```bash
yarn dlx -q npm-check-updates --workspaces --root --format group
```

For each major: read release notes (`gh release view <tag> -R <owner>/<repo>`), grep call
sites, then **ask the user** in one multi-select question with per-package impact (breaking
changes hit, files touched, effort). Respect project pins (e.g. AGENTS.md keeping Tailwind v3).
One major per step; verify after each.

## 8. Verify

Run typecheck, lint, test, build (Turborepo: `turbo run <tasks> --continue` so one failure
doesn't hide others). Diff against the step-1 baseline; to re-check one, `git stash`, run, `git
stash pop`.

## 9. Report

- Alerts fixed (pkg: old → new), dismissed (reason), remaining (why).
- Overrides added (pkg → range, which manager key).
- Majors done vs deferred.
- Checks run with real results; pre-existing failures marked as such.
- GitHub closes alerts only after merge to the default branch.

## Gotchas

- Lint scripts running `eslint --fix` mutate source. Revert unrelated autofix drift
  (`git checkout -- <files>`) to keep the diff dependency-only, or commit it separately.
- "Patch" bumps of shared lint configs can break (new rules, plugin scoping, types). Treat as
  their own step; if not cheaply fixable, revert that package and note it for upstream.
- Never commit or push without explicit approval; messages follow the repo's commitlint (often
  a ticket reference).
