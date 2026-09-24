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


def test_held_out_synonyms_never_leak():
    non_last_normalized = {
        normalize(variant)
        for field, by_lang in HEADERS.items()
        for lang in LANGUAGES
        for variant in by_lang[lang][:-1]
    }

    # 1. The held-out (last) variant of every field/language must never collide
    #    with any non-held-out (dev-visible) variant of any field/language.
    for field, by_lang in HEADERS.items():
        for lang in LANGUAGES:
            last_normalized = normalize(by_lang[lang][-1])
            assert last_normalized not in non_last_normalized, (
                f"held-out synonym leaked into dev aliases: {last_normalized!r} "
                f"(field={field!r}, lang={lang!r})"
            )

    # 2. No normalized header text (any field, language, or position) may be
    #    ambiguous between two different target fields.
    normalized_to_fields: dict[str, set[str]] = {}
    for field, by_lang in HEADERS.items():
        for lang in LANGUAGES:
            for variant in by_lang[lang]:
                normalized_to_fields.setdefault(normalize(variant), set()).add(field)
    ambiguous = {text: fields for text, fields in normalized_to_fields.items() if len(fields) > 1}
    assert not ambiguous, f"header text maps to multiple fields: {ambiguous}"

    # 3. No normalized header text may collide with any distractor text.
    distractor_normalized = {
        normalize(text) for lang in LANGUAGES for text, _kind in DISTRACTORS[lang]
    }
    header_normalized = set(normalized_to_fields)
    collisions = header_normalized & distractor_normalized
    assert not collisions, f"header text collides with distractor text: {collisions}"
