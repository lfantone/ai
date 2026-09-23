---
type: llm
focus: last_message
---
The answer is a checklist of cli verification scenarios for a Redis stream compaction command. All claims must hold to pass.

1. Every scenario runs the real command (`python -m pipeline.compact ...`, via `docker compose exec worker` or equivalent) and its `expect:` is a runtime observation: the exit code, the exact log line, or a Redis value read back with a redis-cli command (such as `XLEN orders` or `EXISTS pipeline:compact:last-run`).
2. No scenario satisfies a criterion by reading, grepping or inspecting source code files (`pipeline/compact.py`, `pipeline/redis_client.py`) instead of running the command.
3. The AC1 scenario has a `pre:` that seeds the stream with acknowledged entries older than 24h (for example XADD with explicit old ids and XACK), and the AC3 scenario has a `pre:` that makes Redis unreachable concretely (stop the redis service or point to a wrong host) and restores it afterwards.
4. Scenarios that create Redis entries are `mutating: yes` and state how they clean up.
