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
