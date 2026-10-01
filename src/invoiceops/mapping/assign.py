"""Column → field assignment. Pairs are {column_index: field_index}."""

import numpy as np
from scipy.optimize import linear_sum_assignment

EPS = 1e-9


def _check_finite(S: np.ndarray) -> None:
    if not np.isfinite(S).all():
        raise ValueError("score matrix contains non-finite values")


def assign_greedy(S: np.ndarray) -> dict[int, int]:
    """Each column takes its best field. Two columns may take the same field (the failure H1 tests)."""
    _check_finite(S)
    return {i: int(S[i].argmax()) for i in range(S.shape[0])}


def assign_hungarian(S: np.ndarray) -> dict[int, int]:
    """One-to-one assignment maximising the total score."""
    _check_finite(S)
    rows, cols = linear_sum_assignment(S, maximize=True)
    return {int(i): int(j) for i, j in zip(rows, cols)}


def pair_margins(S: np.ndarray, pairs: dict[int, int]) -> dict[int, float]:
    """Greedy margin: score minus the best competitor sharing this row or this column."""
    out = {}
    for i, j in pairs.items():
        row_others = np.delete(S[i], j)
        col_others = np.delete(S[:, j], i)
        best_other = max(row_others.max(initial=0.0), col_others.max(initial=0.0))
        out[i] = float(S[i, j] - best_other)
    return out


def _assignment_total(X: np.ndarray) -> float:
    rows, cols = linear_sum_assignment(X, maximize=True)
    return float(X[rows, cols].sum())


def regret_margins(S: np.ndarray, pairs: dict[int, int]) -> dict[int, float]:
    """Hungarian margin: how much the optimal total assignment score would drop if this
    pair were forbidden. Forbidding is modeled by zeroing S[i, j] (equivalent to leaving
    the pair unmatched, since scores are in [0, 1]), then re-solving the assignment.
    Regret is in [0, S[i, j]].
    """
    total = _assignment_total(S)
    out = {}
    for i, j in pairs.items():
        S_prime = S.copy()
        S_prime[i, j] = 0.0
        out[i] = float(total - _assignment_total(S_prime))
    return out


def gate(
    S: np.ndarray,
    pairs: dict[int, int],
    tau: float,
    margin: float,
    margins: dict[int, float],
) -> dict[int, int]:
    """Keep a pair only if its score >= tau and its margin >= margin (within EPS tolerance
    for float rounding); the rest stay unmapped.
    """
    return {
        i: j
        for i, j in pairs.items()
        if S[i, j] >= tau - EPS and margins[i] >= margin - EPS
    }
