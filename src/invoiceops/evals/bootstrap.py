"""Cluster bootstrap: resample whole carriers, because invoices of one carrier are not independent.

Note: percentile cluster-bootstrap CIs are optimistic (too narrow) when the number of clusters is
small (e.g. ~6) — the resampling distribution can't explore enough distinct cluster combinations to
reflect the true between-cluster variance. Treat CIs from few clusters as a lower bound on uncertainty,
not a calibrated interval.
"""

from collections.abc import Callable

import numpy as np


def cluster_bootstrap_ci(
    counts_by_cluster: dict[str, np.ndarray],
    stat: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(point, lo, hi). Each cluster maps to an (n_items, k) count array; stat takes a summed (k,) vector.

    Fewer than 2 clusters: no CI is possible, so (point, nan, nan) is returned. 0 clusters: raises
    ValueError. Any non-finite bootstrap replicate (e.g. a resample whose denominator sums to 0 under
    an unguarded stat) raises ValueError rather than silently poisoning or narrowing the CI.
    """
    keys = sorted(counts_by_cluster)
    if not keys:
        raise ValueError("no clusters")
    for k in keys:
        arr = np.asarray(counts_by_cluster[k])
        if arr.ndim != 2:
            raise ValueError(f"cluster {k!r} count array must be 2-D (n_items, k), got ndim={arr.ndim}")
    totals = np.stack([np.asarray(counts_by_cluster[k]).sum(axis=0) for k in keys])
    point = float(stat(totals.sum(axis=0)))
    if len(keys) < 2:
        return point, float("nan"), float("nan")
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n_boot, len(keys)))
    boots = np.array([stat(totals[i].sum(axis=0)) for i in idx], dtype=float)
    n_bad = int(np.sum(~np.isfinite(boots)))
    if n_bad:
        raise ValueError(f"{n_bad} of {n_boot} bootstrap replicates were non-finite (nan/inf)")
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)
