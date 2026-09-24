from datetime import datetime

import numpy as np

from invoiceops.mapping.stages import AliasStage, EmbedStage, FuzzyStage, build_aliases, infer_kind, type_matrix
from invoiceops.mapping.table import Table
from tests.helpers import fake_encoder

FIELDS = ["amount", "currency"]


def aliases():
    return build_aliases([("Montant HT", "amount"), ("Devise", "currency"), ("Ignored", "not_a_field")], FIELDS)


def table():
    return Table(0, ["MONTANT_HT", "Devise (EUR)", "Destination"], [[1.0, "EUR", "Paris"]])


def test_build_aliases_includes_field_names_and_skips_unknown_fields():
    assert aliases() == {"amount": {"amount", "montant ht"}, "currency": {"currency", "devise"}}


def test_alias_stage_exact_after_normalisation():
    S = AliasStage(aliases(), FIELDS).score(table())
    assert S.tolist() == [[1.0, 0.0], [0.0, 0.0], [0.0, 0.0]]


def test_fuzzy_stage_catches_suffix_and_rejects_unrelated():
    S = FuzzyStage(aliases(), FIELDS).score(table())
    assert S.shape == (3, 2)
    assert S[1, 1] >= 0.75
    assert S[2].max() < 0.7
    assert np.all((S >= 0) & (S <= 1))


def test_fuzzy_does_not_saturate_on_token_subset():
    a = build_aliases([("Amount", "amount")], ["amount"])
    S = FuzzyStage(a, ["amount"]).score(Table(0, ["Amount Prev. Period"], [[1.0]]))
    assert S[0, 0] < 0.9


def test_embed_stage_exact_alias_scores_one_and_caches():
    calls = []

    def counting(texts):
        calls.append(list(texts))
        return fake_encoder(texts)

    stage = EmbedStage(aliases(), FIELDS, counting)
    t = Table(0, ["Montant HT", "Montant HT"], [[1.0, 2.0]])
    S = stage.score(t)
    assert S.shape == (2, 2)
    assert np.isclose(S[0, 0], 1.0)
    stage.score(t)
    assert all("montant ht" not in batch for batch in calls[1:])  # prototype already cached


def test_infer_kind():
    assert infer_kind([datetime(2025, 1, 1), None]) == "date"
    assert infer_kind([1.5, 2]) == "number"
    assert infer_kind(["EUR", "EUR"]) == "currency"
    assert infer_kind(["R1234", "123-00001"]) == "id"
    assert infer_kind(["Voice Paris", "SMS"]) == "text"
    assert infer_kind([None, ""]) == "empty"


def test_type_matrix_rewards_matching_kinds():
    t = Table(0, ["a", "b"], [[10.0, "EUR"], [5.0, "EUR"]])
    M = type_matrix(t, ["amount", "currency"])
    assert M[0, 0] == 1.0 and M[1, 1] == 1.0
    assert M[0, 1] < 0.5 and M[1, 0] < 0.5


def test_infer_kind_currency_requires_known_code_not_just_three_letters():
    assert infer_kind(["SMS", "SMS", "SMS"]) == "text"
    assert infer_kind(["EUR", "USD"]) == "currency"


def test_type_matrix_number_id_partial_compat():
    t = Table(0, ["a"], [["00123"], ["00456"]])
    M = type_matrix(t, ["invoice_no"])
    assert infer_kind(t.column(0)) == "id"
    t2 = Table(0, ["a"], [[123.0], [456.0]])
    M2 = type_matrix(t2, ["invoice_no"])
    assert M2[0, 0] == 0.5
