---
type: llm
focus: last_message
---
The answer is a repository profile brief for a small Express/TypeScript service, and a profile file was written to `.agents/cache/repo-profile.md`. Judge the brief in the answer. All claims must hold to pass.

1. It names the stack (Node, TypeScript, Express, vitest, pnpm, eslint/prettier) and the layout (`src/http`, `src/cache`, `src/lib`).
2. It lists the reviewer-enforced rules from CONTRIBUTING.md: injected `Clock` / no `Date.now()`, logging via `logger` / no `console.*`, `SessionStore` sole owner of the map, tests under `__tests__/` with vitest, `verbNoun` exports and no default exports, Conventional Commits.
3. It names the key modules/helpers by path (for example `src/lib/clock.ts`, `src/cache/session-store.ts`), optionally with symbols, and it does not paste file bodies.
