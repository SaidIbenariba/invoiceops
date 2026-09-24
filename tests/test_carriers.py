import random

from faker import Faker

from invoiceops.mapping.fields import REQUIRED_TABLE_FIELDS
from invoiceops.synth.carriers import N_DISTRACTORS, apply_noise, headers_for, make_carriers
from invoiceops.synth.vocab import HEADERS


def carriers(seed, n=6, held_out=frozenset()):
    fake = Faker("en_US")
    fake.seed_instance(seed)
    return make_carriers(n, random.Random(seed), fake, held_out=held_out)


def test_same_seed_same_carriers():
    assert carriers(1) == carriers(1)
    assert carriers(1) != carriers(2)


def test_required_fields_always_present_and_ids_sequential():
    specs = carriers(3)
    assert [s.carrier_id for s in specs] == [f"C{k:02d}" for k in range(1, 7)]
    for s in specs:
        assert set(REQUIRED_TABLE_FIELDS) <= set(s.fields)


def test_headers_align_with_truth():
    for spec in carriers(4):
        headers, truth = headers_for(spec, "fr")
        assert len(headers) == len(truth) == len(spec.fields) + N_DISTRACTORS
        assert truth.count(None) == N_DISTRACTORS
        assert sorted(t for t in truth if t) == sorted(spec.fields)


def test_description_is_not_mistaken_for_a_distractor():
    specs = [s for s in carriers(5, n=20) if "description" in s.fields]
    assert specs, "seed should produce at least one carrier with a description column"
    _, truth = headers_for(specs[0], "en")
    assert "description" in truth


def test_non_held_out_carriers_never_use_last_variant():
    for spec in carriers(6, n=15):
        headers, truth = headers_for(spec, "en")
        for h, field in zip(headers, truth):
            if field:
                last = apply_noise(HEADERS[field]["en"][-1], spec.noise, field, spec.currency)
                assert h != last


def test_held_out_carriers_use_last_variant_sometimes():
    specs = carriers(7, n=15, held_out=frozenset(f"C{k:02d}" for k in range(1, 16)))
    used = 0
    for spec in specs:
        headers, truth = headers_for(spec, "en")
        for h, field in zip(headers, truth):
            if field and h == apply_noise(HEADERS[field]["en"][-1], spec.noise, field, spec.currency):
                used += 1
    assert used > 0


def test_apply_noise_variants():
    assert apply_noise("Unit Price", "upper", "unit_price", "EUR") == "UNIT PRICE"
    assert apply_noise("Unit Price", "snake", "unit_price", "EUR") == "unit_price"
    assert apply_noise("Amount", "currency_suffix", "amount", "GBP") == "Amount (GBP)"
    assert apply_noise("Destination", "currency_suffix", None, "GBP") == "Destination"
    assert apply_noise("Account Manager", "abbrev", None, "EUR") == "Acco. Mana."
