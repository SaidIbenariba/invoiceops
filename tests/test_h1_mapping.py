import numpy as np

from invoiceops.evals import h1_mapping as h1
from invoiceops.evals.h1_mapping import CONFIGS, TAUS, render_markdown, run_ablation
from tests.helpers import fake_encoder


def test_run_ablation_on_tiny_dataset(tiny_dataset):
    report = run_ablation(tiny_dataset, encoder=fake_encoder, n_boot=50)
    assert [r.config for r in report.rows] == [c.name for c in CONFIGS]
    for r in report.rows:
        assert 0.0 <= r.accuracy[0] <= 1.0
        assert r.accuracy[1] <= r.accuracy[0] <= r.accuracy[2]
        assert r.tau in TAUS
        assert r.silent >= 0
    assert len(report.h1_diff) == 3
    assert report.n_test_files == 2 * 3 * 2  # tiny_dataset: 10 carriers → 2 test carriers


def test_markdown_has_one_row_per_config_and_verdict(tiny_dataset):
    report = run_ablation(tiny_dataset, encoder=fake_encoder, n_boot=50)
    md = render_markdown(report, git_sha="abc1234")
    assert md.count("\n| ") == len(CONFIGS) + 1  # header row + one per config
    assert "**H1**" in md and ("supported" in md)


def test_taus_start_at_010_with_18_values():
    assert TAUS == tuple(round(0.10 + 0.05 * k, 2) for k in range(18))
    assert TAUS[0] == 0.10
    assert TAUS[-1] == 0.95


def test_tune_prefers_lower_refusal_among_equally_accurate_feasible_configs(monkeypatch):
    """Among feasible grid points (0 silent, false-map <= 5%) with identical accuracy, tune()
    must pick the lowest-refusal one, not just the first grid point encountered.
    """

    def fake_run_config(mapper, items, cfg):
        # accuracy and false-map are constant across the grid; refusal is lowest at the
        # highest tau. If tune() ignored refusal, ties on (accuracy, false_map) would leave
        # the first-seen grid point (lowest tau) selected instead.
        refused = round(1.0 - cfg.tau, 2)
        return {"C1": np.array([[8.0, 10.0, 0.0, 8.0, 0.0, refused, 1.0]])}

    monkeypatch.setattr(h1, "run_config", fake_run_config)
    tuned = h1.tune(mapper=None, items=[], config=h1.CONFIGS[0])
    assert tuned.tau == max(h1.TAUS)
