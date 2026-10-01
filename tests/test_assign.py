import numpy as np
import pytest

from invoiceops.mapping.assign import (
    assign_greedy,
    assign_hungarian,
    gate,
    pair_margins,
    regret_margins,
)

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
    assert gate(S, {0: 0, 2: 1}, 0.5, 0.2, pair_margins(S, {0: 0, 2: 1})) == {2: 1}
    assert gate(S, {0: 0, 2: 1}, 0.8, 0.0, pair_margins(S, {0: 0, 2: 1})) == {0: 0}


def test_regret_margin_keeps_correct_pairs_hungarian_resolved():
    R = np.array([[0.95, 0.10], [0.85, 0.99]])
    pairs = assign_hungarian(R)
    assert pairs == {0: 0, 1: 1}

    regrets = regret_margins(R, pairs)
    assert regrets[0] == pytest.approx(0.95)
    assert regrets[1] == pytest.approx(0.99)
    assert regrets[0] >= 0.15
    assert regrets[1] >= 0.15

    # the old (row/column-competitor) margin definition would drop at least one of these
    old_margins = pair_margins(R, pairs)
    assert old_margins[0] < 0.15 or old_margins[1] < 0.15


def test_unassigned_lookalike_does_not_kill_regret():
    D = np.array(
        [
            [0.92, 0.05, 0.05],
            [0.05, 0.90, 0.05],
            [0.05, 0.05, 0.90],
            [0.88, 0.05, 0.05],
        ]
    )
    pairs = assign_hungarian(D)
    assert pairs[0] == 0

    regrets = regret_margins(D, pairs)
    assert regrets[0] == pytest.approx(0.92 - 0.88)


def test_hungarian_can_beat_greedy_after_gate():
    S2 = np.array([[0.9, 0.8], [0.95, 0.1]])

    greedy_pairs = assign_greedy(S2)
    assert greedy_pairs == {0: 0, 1: 0}
    gated_greedy = gate(S2, greedy_pairs, 0.5, 0.0, pair_margins(S2, greedy_pairs))
    assert gated_greedy == {1: 0}

    hungarian_pairs = assign_hungarian(S2)
    assert hungarian_pairs == {0: 1, 1: 0}
    gated_hungarian = gate(
        S2, hungarian_pairs, 0.5, 0.0, regret_margins(S2, hungarian_pairs)
    )
    assert gated_hungarian == {0: 1, 1: 0}


def test_float_tolerance():
    S3 = np.array([[0.9, 0.8]])
    pairs = {0: 0}
    assert gate(S3, pairs, 0.5, 0.1, pair_margins(S3, pairs)) == {0: 0}


def test_non_finite_raises():
    bad = np.array([[0.9, np.nan], [0.8, 0.2]])
    with pytest.raises(ValueError):
        assign_greedy(bad)
    with pytest.raises(ValueError):
        assign_hungarian(bad)
