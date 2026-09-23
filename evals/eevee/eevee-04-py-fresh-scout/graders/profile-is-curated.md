---
type: llm
focus: last_message
---
The answer is a repository profile brief for a small Python ETL, and a profile file was written to `.agents/cache/repo-profile.md`. Judge the brief. All claims must hold to pass.

1. It names the stack: Python 3.12, uv, pytest, ruff, mypy --strict, httpx/redis/confluent-kafka/pydantic.
2. It lists the AGENTS.md rules: walkers subclass `BaseWalker` and register in `pipeline/walkers/__init__.py`; Redis only via `pipeline/redis_client.py`; config only via `pipeline/config.py` and `.env.*` files; `fake_redis` fixture in unit tests; live tests marked `live` fail rather than skip unless `HARBOR_SKIP_LIVE=1`; Conventional Commits.
3. Key modules are cited as `file:symbol`; no file bodies pasted.
