from datetime import date
from decimal import Decimal

from invoiceops.contract import Invoice, Refusal, build_contract


def valid_draft(**overrides):
    draft = {
        "invoice_no": "INV-1",
        "supplier_id": "C01",
        "invoice_date": date(2025, 3, 1),
        "currency": "EUR",
        "net": Decimal("100.00"),
        "tax": Decimal("20.00"),
        "gross": Decimal("120.00"),
        "lines": [{"charge_type": "voice", "amount": Decimal("100.00")}],
    }
    draft.update(overrides)
    return draft


def test_valid_draft_builds_invoice():
    inv = build_contract(valid_draft())
    assert isinstance(inv, Invoice)
    assert inv.lines[0].charge_type.value == "voice"


def test_missing_required_header_field_refuses():
    r = build_contract(valid_draft(invoice_no=None))
    assert isinstance(r, Refusal)
    assert r.reason == "missing_required"
    assert r.missing == ["invoice_no"]


def test_blank_string_counts_as_missing():
    r = build_contract(valid_draft(currency="  "))
    assert isinstance(r, Refusal)
    assert r.missing == ["currency"]


def test_empty_lines_refuses():
    r = build_contract(valid_draft(lines=[]))
    assert isinstance(r, Refusal)
    assert "lines" in r.missing


def test_missing_line_amount_refuses():
    r = build_contract(valid_draft(lines=[{"charge_type": "voice", "amount": None}]))
    assert isinstance(r, Refusal)
    assert r.missing == ["lines[0].amount"]


def test_tax_missing_allowed_when_gross_equals_net():
    inv = build_contract(valid_draft(tax=None, gross=Decimal("100.00")))
    assert isinstance(inv, Invoice)
    assert inv.tax is None


def test_tax_missing_refused_when_gross_differs():
    r = build_contract(valid_draft(tax=None))
    assert isinstance(r, Refusal)
    assert r.reason == "tax_missing_and_gross_ne_net"
    assert r.missing == ["tax"]


def test_invalid_currency_refuses_with_field_name():
    r = build_contract(valid_draft(currency="eur"))
    assert isinstance(r, Refusal)
    assert r.reason == "invalid"
    assert "currency" in r.missing


def test_unknown_charge_type_refuses():
    r = build_contract(valid_draft(lines=[{"charge_type": "roaming", "amount": Decimal("1")}]))
    assert isinstance(r, Refusal)
    assert r.reason == "invalid"
    assert "lines.0.charge_type" in r.missing
