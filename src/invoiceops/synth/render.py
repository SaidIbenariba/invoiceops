"""Ground-truth invoice records and their rendering as a carrier XLSX file."""

import random
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from faker import Faker
from openpyxl import Workbook

from invoiceops.mapping.fields import CHARGE_LABELS
from invoiceops.synth.carriers import DISTRACTOR_PREFIX, CarrierSpec, headers_for
from invoiceops.synth.vocab import BANNERS, DISTRACTORS

CENT = Decimal("0.01")


def make_invoice(spec: CarrierSpec, lang: str, rng: random.Random, fake: Faker, seq: int) -> dict:
    lines = []
    pool = sorted(CHARGE_LABELS)
    n = rng.randint(3, 12)
    charges = rng.sample(pool, 2) + [rng.choice(pool) for _ in range(n - 2)]
    for charge in charges:
        if charge == "recurring":
            quantity, unit_price = Decimal(1), Decimal(rng.randint(100, 5000))
        else:
            quantity, unit_price = Decimal(rng.randint(100, 50000)), Decimal(rng.randint(10, 2000)) / Decimal(10000)
        lines.append(
            {
                "charge_type": charge,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": (quantity * unit_price).quantize(CENT, ROUND_HALF_UP),
                "description": f"{CHARGE_LABELS[charge][lang]} {fake.city()}",
            }
        )
    net = sum((line["amount"] for line in lines), Decimal(0))
    tax = (net * Decimal(spec.tax_rate)).quantize(CENT, ROUND_HALF_UP)
    return {
        "invoice_no": f"{rng.randint(100, 999)}-{seq:05d}",
        "supplier_id": spec.carrier_id,
        "invoice_date": date(2025, 1, 1) + timedelta(days=rng.randrange(365)),
        "currency": spec.currency,
        "net": net,
        "tax": tax,
        "gross": net + tax,
        "lines": lines,
    }


def _distractor_value(kind: str, rng: random.Random, fake: Faker) -> object:
    if kind == "text":
        return fake.city()
    if kind == "id":
        return f"R{rng.randint(1000, 9999)}"
    return round(rng.uniform(0, 1000), 2)


def _cell(key: str, line: dict, record: dict, spec: CarrierSpec, lang: str, rng: random.Random, fake: Faker) -> object:
    if key.startswith(DISTRACTOR_PREFIX):
        _, kind = DISTRACTORS[lang][spec.distractor_ids[int(key[1:])]]
        return _distractor_value(kind, rng, fake)
    if key in ("invoice_no", "invoice_date", "currency"):
        return record[key]
    if key == "charge_type":
        return CHARGE_LABELS[line["charge_type"]][lang]
    if key == "description":
        return line["description"]
    return float(line[key])  # quantity, unit_price, amount


def write_xlsx(path: Path, spec: CarrierSpec, lang: str, record: dict, rng: random.Random, fake: Faker) -> dict:
    """Write one invoice. Returns ground truth: header row index, header texts, field per column."""
    wb = Workbook()
    wb.properties.created = wb.properties.modified = datetime(2026, 1, 1)
    ws = wb.active
    period = record["invoice_date"].strftime("%Y-%m")
    for i in range(spec.n_banner_rows):
        ws.append([BANNERS[lang][i].format(carrier=spec.name, period=period)] if i < len(BANNERS[lang]) else [])
    headers, truth = headers_for(spec, lang)
    ws.append(headers)
    for line in record["lines"]:
        ws.append([_cell(key, line, record, spec, lang, rng, fake) for key in spec.column_order])
    wb.save(path)
    return {"header_row": spec.n_banner_rows, "headers": headers, "mapping": truth}
