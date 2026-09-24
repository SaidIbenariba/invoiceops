import numpy as np

from invoiceops.evals.bootstrap import cluster_bootstrap_ci


def ratio(c):
    return c[0] / c[1]


def test_identical_clusters_give_zero_width_ci():
    counts = {k: np.array([[1.0, 2.0]]) for k in "abcde"}
    assert cluster_bootstrap_ci(counts, ratio, n_boot=200, seed=1) == (0.5, 0.5, 0.5)


def test_ci_brackets_point_and_is_deterministic():
    counts = {
        "a": np.array([[1.0, 1.0]]),
        "b": np.array([[0.0, 1.0]]),
        "c": np.array([[1.0, 1.0], [1.0, 1.0]]),
        "d": np.array([[0.0, 1.0]]),
    }
    r1 = cluster_bootstrap_ci(counts, ratio, n_boot=500, seed=3)
    r2 = cluster_bootstrap_ci(counts, ratio, n_boot=500, seed=3)
    assert r1 == r2
    assert r1[0] == 0.6
    assert r1[1] <= r1[0] <= r1[2] and r1[1] < r1[2]
