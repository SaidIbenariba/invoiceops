"""Cluster bootstrap: resample whole carriers, because invoices of one carrier are not independent."""

from collections.abc import Callable

import numpy as np


def cluster_bootstrap_ci(
    counts_by_cluster: dict[str, np.ndarray],
    stat: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(point, lo, hi). Each cluster maps to an (n_items, k) count array; stat takes a summed (k,) vector."""
    keys = sorted(counts_by_cluster)
    totals = np.stack([np.asarray(counts_by_cluster[k]).sum(axis=0) for k in keys])
    point = float(stat(totals.sum(axis=0)))
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n_boot, len(keys)))
    boots = np.array([stat(totals[i].sum(axis=0)) for i in idx])
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)
