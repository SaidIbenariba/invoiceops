"""Column → field assignment. Pairs are {column_index: field_index}."""

import numpy as np
from scipy.optimize import linear_sum_assignment


def assign_greedy(S: np.ndarray) -> dict[int, int]:
    """Each column takes its best field. Two columns may take the same field (the failure H1 tests)."""
    return {i: int(S[i].argmax()) for i in range(S.shape[0])}


def assign_hungarian(S: np.ndarray) -> dict[int, int]:
    """One-to-one assignment maximising the total score."""
    rows, cols = linear_sum_assignment(S, maximize=True)
    return {int(i): int(j) for i, j in zip(rows, cols)}


def pair_margins(S: np.ndarray, pairs: dict[int, int]) -> dict[int, float]:
    """Score minus the best competitor: other fields for this column, or other columns for this field."""
    out = {}
    for i, j in pairs.items():
        row_others = np.delete(S[i], j)
        col_others = np.delete(S[:, j], i)
        best_other = max(row_others.max(initial=0.0), col_others.max(initial=0.0))
        out[i] = float(S[i, j] - best_other)
    return out


def gate(S: np.ndarray, pairs: dict[int, int], tau: float, margin: float) -> dict[int, int]:
    """Keep a pair only if its score >= tau and its margin >= margin; the rest stay unmapped."""
    margins = pair_margins(S, pairs)
    return {i: j for i, j in pairs.items() if S[i, j] >= tau and margins[i] >= margin}
