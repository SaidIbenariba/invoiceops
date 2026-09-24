import math

import numpy as np
import pytest

from invoiceops.evals.bootstrap import cluster_bootstrap_ci


def ratio(c):
    return c[0] / c[1]


def unguarded_ratio(c):
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


def test_single_cluster_gives_nan_ci_but_finite_point():
    counts = {"a": np.array([[1.0, 2.0]])}
    point, lo, hi = cluster_bootstrap_ci(counts, ratio, n_boot=50, seed=1)
    assert point == 0.5
    assert math.isnan(lo) and math.isnan(hi)


def test_zero_clusters_raises():
    with pytest.raises(ValueError, match="no clusters"):
        cluster_bootstrap_ci({}, ratio, n_boot=50, seed=1)


def test_non_finite_replicate_raises():
    counts = {
        "a": np.array([[0.0, 0.0]]),
        "b": np.array([[1.0, 2.0]]),
    }
    with pytest.raises(ValueError, match="non-finite"):
        cluster_bootstrap_ci(counts, unguarded_ratio, n_boot=200, seed=1)


def test_one_dimensional_cluster_array_raises():
    counts = {"a": np.array([1.0, 2.0]), "b": np.array([1.0, 2.0])}
    with pytest.raises(ValueError, match="2-D|2D|two-dimensional|ndim"):
        cluster_bootstrap_ci(counts, ratio, n_boot=50, seed=1)
