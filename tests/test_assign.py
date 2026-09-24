import numpy as np
import pytest

from invoiceops.mapping.assign import assign_greedy, assign_hungarian, gate, pair_margins

S = np.array([[0.9, 0.1], [0.8, 0.2], [0.1, 0.7]])


def test_greedy_allows_two_columns_on_one_field():
    assert assign_greedy(S) == {0: 0, 1: 0, 2: 1}


def test_hungarian_is_one_to_one():
    pairs = assign_hungarian(S)
    assert pairs == {0: 0, 2: 1}
    assert len(set(pairs.values())) == len(pairs)


def test_margin_is_min_of_row_and_column_competition():
    m = pair_margins(S, {0: 0, 2: 1})
    assert m[0] == pytest.approx(0.1)  # column 1 competes for field 0 at 0.8
    assert m[2] == pytest.approx(0.5)  # best competitor 0.2


def test_gate_drops_low_score_or_low_margin():
    assert gate(S, {0: 0, 2: 1}, tau=0.5, margin=0.2) == {2: 1}
    assert gate(S, {0: 0, 2: 1}, tau=0.8, margin=0.0) == {0: 0}
