"""Per-file mapping counts. Ratios are computed from summed counts, so bootstrap resamples stay exact."""

import numpy as np

from invoiceops.mapping import MappingResult

COUNT_KEYS = ("correct", "n_target", "wrong", "n_mapped", "silent", "refused", "n_files")
CORRECT, N_TARGET, WRONG, N_MAPPED, SILENT, REFUSED, N_FILES = range(len(COUNT_KEYS))


def file_counts(result: MappingResult, truth: list[str | None], refused: bool) -> np.ndarray:
    """A record is silently wrong if it was emitted (not refused) with any wrong column assignment."""
    correct = sum(1 for i, f in result.assignments.items() if truth[i] == f)
    wrong = len(result.assignments) - correct
    n_target = sum(1 for t in truth if t is not None)
    silent = int(not refused and wrong > 0)
    return np.array([correct, n_target, wrong, len(result.assignments), silent, int(refused), 1], dtype=float)


def accuracy(c: np.ndarray) -> float:
    return float(c[CORRECT] / c[N_TARGET]) if c[N_TARGET] else 0.0


def false_map_rate(c: np.ndarray) -> float:
    return float(c[WRONG] / c[N_MAPPED]) if c[N_MAPPED] else 0.0


def refusal_rate(c: np.ndarray) -> float:
    return float(c[REFUSED] / c[N_FILES]) if c[N_FILES] else 0.0
