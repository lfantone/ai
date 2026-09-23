---
max_turns: 14
timeout_seconds: 600
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
plugins: [../../..]
model: sonnet
runs: 5
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

`README.md`:

```md
# harbor-etl

Nightly Python ETL that pulls collections from the Harbor gateway and publishes them to Kafka.

- Python 3.12, managed with `uv`. `uv run pytest` runs the tests, `uv run ruff check .` lints.
- Layout: `pipeline/` (collection walkers, cursors, writers), `pipeline/redis_client.py`
  (all Redis access), `tests/`.
- Configuration comes only from `.env.*` files loaded by `pipeline/config.py`; never read
  `os.environ` directly elsewhere.
```

`AGENTS.md`:

```md
# Working in this repo

- Every collection walker is a subclass of `pipeline.walkers.BaseWalker` and is registered in
  `pipeline/walkers/__init__.py`; do not special-case collections in `main.py`.
- Redis is only touched through `pipeline/redis_client.py` (connection timeout 2s, raises
  `RedisUnavailable`); no bare `redis.Redis()` anywhere else.
- Tests use `pytest` with the `fake_redis` fixture from `tests/conftest.py`; no live Redis in
  unit tests. Live-API tests are marked `@pytest.mark.live` and FAIL (not skip) when the API is
  unreachable unless `HARBOR_SKIP_LIVE=1`.
- Type hints everywhere; `ruff` and `mypy --strict` must pass.
- Commit messages: Conventional Commits.
```

`pyproject.toml`:

```toml
[project]
name = "harbor-etl"
version = "0.4.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "redis>=5.0", "confluent-kafka>=2.5", "pydantic>=2.8"]

[tool.uv]
dev-dependencies = ["pytest>=8.3", "ruff>=0.6", "mypy>=1.11"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B"]

[tool.pytest.ini_options]
markers = ["live: hits the real Harbor API"]
```

`pipeline/config.py`:

```py
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    kafka_bootstrap: str
    redis_url: str
    harbor_base_url: str


def load_settings(env: str) -> Settings:
    """Load `.env.<env>`; the only place that reads environment files."""
    values = dict(line.split("=", 1) for line in Path(f".env.{env}").read_text().splitlines() if "=" in line)
    return Settings(**{k.lower(): v for k, v in values.items()})
```

`pipeline/redis_client.py`:

```py
import redis


class RedisUnavailable(RuntimeError):
    pass


def connect(url: str) -> redis.Redis:
    """The only Redis entry point in the codebase."""
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        client.ping()
        return client
    except redis.exceptions.ConnectionError as exc:
        raise RedisUnavailable(str(exc)) from exc
```

`pipeline/walkers/__init__.py`:

```py
from .base import BaseWalker
from .readings import ReadingsWalker

REGISTRY: dict[str, type[BaseWalker]] = {"Readings": ReadingsWalker}
```

`pipeline/walkers/base.py`:

```py
from abc import ABC, abstractmethod


class BaseWalker(ABC):
    collection: str

    @abstractmethod
    def walk(self, since: str | None) -> list[dict]:
        ...
```

`pipeline/walkers/readings.py`:

```py
from .base import BaseWalker


class ReadingsWalker(BaseWalker):
    collection = "Readings"
    cursor_field = "Submitted"

    def walk(self, since: str | None) -> list[dict]:
        return []
```

`tests/conftest.py`:

```py
import pytest


@pytest.fixture
def fake_redis():
    class Fake:
        store: dict[str, str] = {}
    return Fake()
```
Step 2 — with a sub-agent, produce the repository profile for this working tree. Do not profile it yourself. Context for the sub-agent: `$CACHE` is `.agents/cache` (relative to the working tree root); git is not available in this environment, so treat the current HEAD as `b7e2d9c4a1f0e3d6c5b8a7f2e1d0c9b8a7f6e5d4` and the working tree as clean with no uncommitted changes. Relay the sub-agent's brief verbatim and nothing else.

