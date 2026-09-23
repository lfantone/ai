---
type: llm
focus: last_message
---
The answer maps a change that keys rate limiting on the authenticated user id instead of the client IP. All claims must hold to pass.

1. Insertion points name `src/http/rate-limit-middleware.ts:rateLimitMiddleware` (the `store.hit(req.ip ...)` key) and note that `RateLimitStore` itself keys on an opaque string and may not need to change.
2. Prior art names `src/http/session-middleware.ts:sessionMiddleware` as the place that resolves the session and sets `req.session`.
3. Collisions or seams name the middleware ordering constraint: the session must be resolved before the rate limiter runs, so the chain order (or the limiter reading `req.session`) is a side effect to handle, and the existing `src/cache/__tests__/rate-limit-store.test.ts` keys on an IP string.
4. No file bodies are pasted.
