---
max_turns: 14
timeout_seconds: 600
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
model: sonnet
runs: 5
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

`README.md`:

```md
# harbor-sessions

Express + TypeScript service that owns login sessions for the Harbor Booking Gateway.

- Runtime: Node 22, pnpm. `pnpm dev` starts the server on :3000, `pnpm test` runs vitest.
- Layout: `src/http` (Express handlers and middleware), `src/cache` (in-memory stores),
  `src/lib` (shared helpers: clock, logger, safe paths).
- All time comes from the injected `Clock` (`src/lib/clock.ts`); `Date.now()` is banned outside it.
```

`CONTRIBUTING.md`:

```md
# Contributing

Rules a reviewer must enforce:

1. Library code takes an injected `Clock`; `Date.now()` only inside `src/lib/clock.ts`.
2. Logging goes through `src/lib/logger.ts` (`debug`/`info`/`warn`); no `console.*` in `src/`.
3. `SessionStore` is the only owner of the session map; middleware goes through its methods.
4. Tests live next to the code under `__tests__/`, one `describe` per unit, vitest only.
5. Exported functions are named `verbNoun` (`createSession`, `evictIdle`); no default exports.
6. Commits follow Conventional Commits (`feat(scope): ...`).
```

`package.json`:

```json
{
  "name": "harbor-sessions",
  "private": true,
  "packageManager": "pnpm@9",
  "scripts": { "dev": "tsx watch src/server.ts", "test": "vitest run", "lint": "eslint src --max-warnings 0", "format": "prettier --check ." },
  "dependencies": { "express": "^4.19.0" },
  "devDependencies": { "typescript": "^5.6.0", "vitest": "^2.1.0", "eslint": "^9.10.0", "prettier": "^3.3.0", "tsx": "^4.19.0" }
}
```

`.prettierrc.json`:

```json
{ "printWidth": 100, "singleQuote": false, "semi": true }
```

`eslint.config.js`:

```ts
export default [
  { files: ["src/**/*.ts"], rules: { "no-console": "error", "no-restricted-syntax": ["error", { selector: "CallExpression[callee.object.name='Date'][callee.property.name='now']", message: "use the injected Clock" }] } },
];
```

`src/lib/clock.ts`:

```ts
export interface Clock {
  now(): number;
}

export const systemClock: Clock = { now: () => Date.now() };
```

`src/lib/logger.ts`:

```ts
export const logger = {
  debug: (msg: string): void => console.debug(msg),
  info: (msg: string): void => console.info(msg),
  warn: (msg: string): void => console.warn(msg),
};
```

`src/cache/session-store.ts`:

```ts
import { logger } from "../lib/logger";

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, SessionRecord>();

  createSession(record: SessionRecord): void {
    this.sessions.set(record.id, record);
  }

  getSession(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }
}
```

`src/http/session-middleware.ts`:

```ts
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionStore } from "../cache/session-store";

export function requireSession(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = store.getSession(req.cookies?.sid);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
```

`src/cache/__tests__/session-store.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { SessionStore } from "../session-store";

describe("SessionStore", () => {
  it("returns a created session", () => {
    const store = new SessionStore();
    store.createSession({ id: "a", userId: "u-1", createdAt: 0 });
    expect(store.getSession("a")?.userId).toBe("u-1");
  });
});
```
Step 2 — list the npm scripts defined in `package.json` with a one-line description each. Do not profile the repository and do not delegate.
