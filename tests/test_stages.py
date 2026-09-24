import numpy as np

from invoiceops.mapping.stages import AliasStage, FuzzyStage, build_aliases
from invoiceops.mapping.table import Table

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
