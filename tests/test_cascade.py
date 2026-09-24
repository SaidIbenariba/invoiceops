import json
from datetime import date, datetime
from decimal import Decimal

from invoiceops.contract import Invoice, Refusal, build_contract
from invoiceops.mapping import CascadeConfig, Mapper, Table, build_aliases, load_table, to_draft
from invoiceops.mapping.fields import TABLE_FIELDS
from tests.helpers import fake_encoder

HEADERS = ["Invoice No", "Date facture", "Currency", "Service", "Amount", "Destination"]
TABLE = Table(
    0,
    HEADERS,
    [
        ["A-1", datetime(2025, 1, 5), "EUR", "Voice", 10.5, "Paris"],
        ["A-1", datetime(2025, 1, 5), "EUR", "SMS", 4.5, "Lyon"],
    ],
)
TRUTH = ["invoice_no", "invoice_date", "currency", "charge_type", "amount"]
ALIAS_ONLY = CascadeConfig("alias", ("alias",), assignment="hungarian", tau=0.5)


def mapper(pairs):
    return Mapper(build_aliases(pairs, TABLE_FIELDS), encoder=fake_encoder)


def test_alias_mapping_builds_valid_invoice():
    m = mapper(zip(HEADERS, TRUTH))
    result = m.decide(TABLE, m.score(TABLE, ALIAS_ONLY), ALIAS_ONLY)
    assert result.assignments == dict(enumerate(TRUTH))
    assert result.unmapped_required == []
    inv = build_contract(to_draft(TABLE, result, "C01"))
    assert isinstance(inv, Invoice)
    assert inv.net == Decimal("15.0")
    assert inv.invoice_date == date(2025, 1, 5)
    assert [line.charge_type.value for line in inv.lines] == ["voice", "sms"]


def test_unmapped_required_field_leads_to_refusal():
    m = mapper(zip(HEADERS[:4], TRUTH[:4]))  # no alias for Amount
    result = m.decide(TABLE, m.score(TABLE, ALIAS_ONLY), ALIAS_ONLY)
    assert "amount" in result.unmapped_required
    assert isinstance(build_contract(to_draft(TABLE, result, "C01")), Refusal)


def test_all_configs_run_on_generated_file(tiny_dataset):
    manifest = json.loads((tiny_dataset / "manifest.json").read_text())
    e = manifest["entries"][0]
    m = mapper(zip(e["headers"], e["mapping"]))
    table = load_table(tiny_dataset / e["path"])
    for cfg in [
        CascadeConfig("b1", ("alias", "fuzzy"), assignment="greedy", tau=0.7),
        CascadeConfig("s4", ("alias", "fuzzy", "embed"), use_types=True, assignment="hungarian", tau=0.7),
    ]:
        result = m.decide(table, m.score(table, cfg), cfg)
        for i, f in result.assignments.items():
            assert e["mapping"][i] == f  # own headers are aliases: every kept pair is right
