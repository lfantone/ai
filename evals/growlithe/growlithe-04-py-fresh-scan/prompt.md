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

Flask admin API + nightly ETL. SQLite via raw `sqlite3`, Redis via `pipeline/redis_client.py`,
secrets from `.env.*` through `pipeline/config.py`.
```

`pipeline/config.py`:

```py
from pathlib import Path


def load_settings(env: str) -> dict[str, str]:
    """The only place that reads `.env.<env>`; values include KAFKA_SASL_PASSWORD. Never log the dict."""
    return dict(line.split("=", 1) for line in Path(f".env.{env}").read_text().splitlines() if "=" in line)
```

`pipeline/db.py`:

```py
import sqlite3


def query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    """The only SQL entry point. Callers must pass params; f-strings into `sql` are forbidden."""
    return conn.execute(sql, params).fetchall()
```

`pipeline/auth.py`:

```py
from functools import wraps
from flask import abort, request


def require_operator(view):
    """Safe path: every /admin/* view must be wrapped with this decorator."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Operator-Token") != current_token():
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def current_token() -> str:
    return "rotated-nightly"
```

`pipeline/api.py`:

```py
import subprocess
from flask import Flask, jsonify, request
from .auth import require_operator
from .db import query

app = Flask(__name__)


@app.post("/admin/replay")
@require_operator
def replay():
    stream = request.json.get("stream", "")
    subprocess.run(["python", "-m", "pipeline.replay", "--stream", stream], check=True)
    return jsonify(ok=True)


@app.get("/admin/runs/<run_id>")
@require_operator
def run_detail(run_id: str):
    rows = query(app.config["DB"], "SELECT * FROM runs WHERE id = ?", (run_id,))
    return jsonify(rows)


@app.post("/hooks/harbor")
def harbor_hook():
    # TODO: verify signature (HARBOR_WEBHOOK_SECRET) before accepting
    return ("", 202)
```
Step 2 — with a sub-agent, produce the security profile (the ranked, repo-specific threat checklist) for this working tree. Do not produce it yourself. Context for the sub-agent: `$CACHE` is `.agents/cache` (relative to the working tree root); git is not available in this environment, so treat the current HEAD as `b7e2d9c4a1f0e3d6c5b8a7f2e1d0c9b8a7f6e5d4` and the working tree as clean with no uncommitted changes. Relay the sub-agent's checklist verbatim and nothing else.

