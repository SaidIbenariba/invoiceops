import json

import pytest

from invoiceops.mapping.table import load_table, table_from_rows


def test_header_found_below_banner_and_body_stops_at_blank_row():
    rows = [
        ["Acme — statement", None, None],
        [None, None, None],
        ["Invoice No", "Amount", "Currency"],
        ["A1", 10.0, "EUR"],
        ["A1", 5.0, "EUR"],
        [None, None, None],
        ["Total", 15.0, None],
    ]
    t = table_from_rows(rows)
    assert t.header_row == 2
    assert t.headers == ["Invoice No", "Amount", "Currency"]
    assert len(t.rows) == 2
    assert t.column(1) == [10.0, 5.0]


def test_no_header_raises():
    with pytest.raises(ValueError, match="header"):
        table_from_rows([["x"], [1]])


def test_csv_numbers_are_coerced(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("Invoice No,Amount,Currency\nA1,10.5,EUR\n", encoding="utf-8")
    t = load_table(p)
    assert t.header_row == 0
    assert t.rows[0][1] == 10.5


def test_header_row_recovered_on_generated_files(tiny_dataset):
    manifest = json.loads((tiny_dataset / "manifest.json").read_text())
    for e in manifest["entries"]:
        t = load_table(tiny_dataset / e["path"])
        assert t.header_row == e["header_row"], e["path"]
        assert t.headers == e["headers"]
