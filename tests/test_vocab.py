from invoiceops.contract import ChargeType
from invoiceops.mapping.fields import CHARGE_LABELS, CHARGE_LOOKUP, FIELD_TYPES, REQUIRED_TABLE_FIELDS, TABLE_FIELDS
from invoiceops.mapping.text import normalize
from invoiceops.synth.vocab import BANNERS, DISTRACTORS, HEADERS, LANGUAGES


def test_normalize_strips_accents_case_and_punctuation():
    assert normalize("Coût trafic entrant") == "cout trafic entrant"
    assert normalize("N° facture") == "n facture"
    assert normalize("Inv #") == "inv"
    assert normalize("MONTANT_HT") == "montant ht"


def test_required_fields_are_table_fields():
    assert set(REQUIRED_TABLE_FIELDS) <= set(TABLE_FIELDS)
    assert set(FIELD_TYPES) == set(TABLE_FIELDS)


def test_every_field_has_at_least_two_variants_per_language():
    assert set(HEADERS) == set(TABLE_FIELDS)
    for field, by_lang in HEADERS.items():
        for lang in LANGUAGES:
            assert len(by_lang[lang]) >= 2, (field, lang)


def test_distractors_and_banners_cover_all_languages():
    for lang in LANGUAGES:
        assert len(DISTRACTORS[lang]) == 8
        assert {kind for _, kind in DISTRACTORS[lang]} <= {"text", "id", "number"}
        assert len(BANNERS[lang]) == 2


def test_charge_labels_map_to_contract_enum():
    assert set(CHARGE_LABELS) <= {c.value for c in ChargeType}
    assert CHARGE_LOOKUP["voix"] == "voice"
    assert CHARGE_LOOKUP["datos"] == "data"
