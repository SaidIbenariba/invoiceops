import random
from decimal import ROUND_HALF_UP, Decimal

import pytest
from faker import Faker
from openpyxl import load_workbook

from invoiceops.contract import Invoice, build_contract
from invoiceops.synth.carriers import make_carriers
from invoiceops.synth.render import make_invoice, write_xlsx


def setup(seed):
    rng = random.Random(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)
    return make_carriers(1, rng, fake)[0], rng, fake


@pytest.mark.parametrize("seed", range(20))
def test_invoice_totals_are_consistent(seed):
    spec, rng, fake = setup(seed)
    rec = make_invoice(spec, "fr", rng, fake, 0)
    assert rec["net"] == sum(line["amount"] for line in rec["lines"])
    assert rec["gross"] == rec["net"] + rec["tax"]
    for line in rec["lines"]:
        assert line["amount"] == (line["quantity"] * line["unit_price"]).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert isinstance(build_contract(rec), Invoice)


@pytest.mark.parametrize("seed", range(10))
def test_xlsx_header_row_matches_meta(seed, tmp_path):
    spec, rng, fake = setup(seed)
    rec = make_invoice(spec, "es", rng, fake, 1)
    meta = write_xlsx(tmp_path / "x.xlsx", spec, "es", rec, rng, fake)
    rows = [list(r) for r in load_workbook(tmp_path / "x.xlsx").active.iter_rows(values_only=True)]
    assert meta["header_row"] == spec.n_banner_rows
    assert rows[meta["header_row"]] == meta["headers"]
    assert len(rows) == meta["header_row"] + 1 + len(rec["lines"])
    assert len(meta["mapping"]) == len(meta["headers"])
    data_rows = rows[meta["header_row"] + 1 :]
    for col, field in enumerate(meta["mapping"]):
        if field == "amount":
            for row, line in zip(data_rows, rec["lines"]):
                assert Decimal(str(row[col])) == line["amount"]
        elif field == "currency":
            for row in data_rows:
                assert row[col] == spec.currency


@pytest.mark.parametrize("seed", range(200))
def test_invoice_has_at_least_two_charge_types(seed):
    spec, rng, fake = setup(seed)
    rec = make_invoice(spec, "fr", rng, fake, 0)
    assert len({line["charge_type"] for line in rec["lines"]}) >= 2


def test_xlsx_bytes_are_reproducible(tmp_path):
    seed = 0
    spec, rng, fake = setup(seed)
    rec = make_invoice(spec, "es", rng, fake, 1)

    rng2 = random.Random(seed)
    fake2 = Faker("en_US")
    fake2.seed_instance(seed)

    write_xlsx(tmp_path / "a.xlsx", spec, "es", rec, rng2, fake2)

    rng3 = random.Random(seed)
    fake3 = Faker("en_US")
    fake3.seed_instance(seed)
    write_xlsx(tmp_path / "b.xlsx", spec, "es", rec, rng3, fake3)

    assert (tmp_path / "a.xlsx").read_bytes() == (tmp_path / "b.xlsx").read_bytes()
