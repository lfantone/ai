---
type: llm
focus: last_message
---
The answer maps where an idle-TTL change to `SessionStore` and `sessionMiddleware` lands in a small TypeScript tree. All claims must hold to pass.

1. Insertion points name `src/cache/session-store.ts` (`SessionRecord` and/or `SessionStore`) and `src/http/session-middleware.ts:sessionMiddleware`, and a new test file under `src/cache/__tests__/`.
2. Prior art names `RateLimitStore.sweep` in `src/cache/rate-limit-store.ts` as the lookup-time sweep to mirror (caller-supplied `now`, `logger.debug` on expiry) and `rateLimitMiddleware` in `src/http/rate-limit-middleware.ts` as the sweep-then-act middleware shape, and `src/cache/__tests__/rate-limit-store.test.ts` as the test shape.
3. Seams name the injected `Clock` (`src/lib/clock.ts`) as the time source; `Date.now()` is not proposed.
4. Collisions name `src/http/routes/me.ts:meHandler`, which serialises `SessionRecord` and would need a decision on exposing `lastSeenAt`.
5. No file bodies are pasted; locations are cited as `file:symbol`.
