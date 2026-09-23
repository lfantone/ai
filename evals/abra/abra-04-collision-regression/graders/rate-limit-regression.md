---
type: llm
focus: last_message
---
The answer is a checklist of verification scenarios. All claims must hold to pass.

1. At least one scenario is a regression check for the collision area named in the change map: rate limiting still returns 429 after the 21st request within a minute from one IP, and requests under the limit still succeed. Its `criterion:` labels it as a regression or collision check rather than one of AC1..AC3.
2. The cli scenarios run the exact command (`npm run sessions -- prune` and the `--dry-run` variant) and expect the exact stdout text (`pruned <n> sessions`) and exit code 0.
3. The dry-run scenario verifies that nothing was deleted (for example a follow-up `GET /api/me` with an idle session still returns 200, or a second prune reports the same count).
