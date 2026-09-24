import sqlite3

from invoiceops.evals.store import record_metrics


def test_record_metrics_appends_rows(tmp_path):
    db = tmp_path / "runs.sqlite"
    record_metrics(db, "run1", "hash", "h1", "B0", {"accuracy": (0.8, 0.7, 0.9), "silent": (0.0, None, None)})
    record_metrics(db, "run2", "hash", "h1", "B0", {"accuracy": (0.85, 0.75, 0.95)})
    with sqlite3.connect(db) as con:
        rows = con.execute("SELECT run_id, metric, value, ci_lo FROM eval_runs ORDER BY run_id, metric").fetchall()
    assert rows == [("run1", "accuracy", 0.8, 0.7), ("run1", "silent", 0.0, None), ("run2", "accuracy", 0.85, 0.75)]
