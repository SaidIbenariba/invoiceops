"""Append-only eval history in SQLite (D009)."""

import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT, created_at TEXT, git_sha TEXT, data_hash TEXT,
    component TEXT, config TEXT, metric TEXT, value REAL, ci_lo REAL, ci_hi REAL
)"""


def git_sha() -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def record_metrics(
    db_path: Path,
    run_id: str,
    data_hash: str,
    component: str,
    config: str,
    metrics: dict[str, tuple[float, float | None, float | None]],
) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    now, sha = datetime.now(timezone.utc).isoformat(), git_sha()
    rows = [(run_id, now, sha, data_hash, component, config, name, v, lo, hi) for name, (v, lo, hi) in metrics.items()]
    with sqlite3.connect(db_path) as con:
        con.execute(SCHEMA)
        con.executemany("INSERT INTO eval_runs VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
