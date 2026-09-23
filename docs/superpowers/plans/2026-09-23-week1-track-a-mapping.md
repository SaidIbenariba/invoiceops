# Week 1 — Track A Mapping (F1–F5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the canonical invoice contract, a seeded synthetic carrier-spreadsheet generator with a leakage-proof split, the column-mapping cascade, and the H1 ablation table with carrier-clustered bootstrap CIs.

**Architecture:** `contract/` defines `Invoice | Refusal` (spec §2.2). `synth/` generates XLSX invoices plus ground truth. `mapping/` recovers the header row, scores every column against every field with pluggable stages (alias, fuzzy, embed, value types), assigns columns to fields (greedy or Hungarian), and gates each assignment on score τ and margin m. `evals/` tunes τ/m on dev carriers, scores the frozen test carriers, and writes results to SQLite and a Markdown table.

**Tech Stack:** Python 3.12, uv, Pydantic v2, Faker, openpyxl, RapidFuzz, NumPy, SciPy, sentence-transformers, pytest.

**Spec:** [docs/design/system-design.md](../../design/system-design.md) §2.1–§2.6, §3, §4 (F1–F5).

**Conventions**
- Run everything with `uv run` from the repo root.
- Every commit message ends with the trailer line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (shown as a second `-m` below).
- Tests live flat in `tests/` (`tests/__init__.py` already exists); shared helpers go in `tests/helpers.py`, fixtures in `tests/conftest.py`.

**Deliberate scope notes (vs. spec)**
- Score stages are combined by **mean** of enabled stage matrices, then multiplied by value-type compatibility. A pure `max` would let a fuzzy hit on a distractor ("Amount Prev. Period") tie the true column.
- Test carriers use **held-out header synonyms** (~50% of fields) — the scoping §9 mitigation "held-out template families", so H1 measures generalisation to unseen names.
- Not in v1 generator: pivot blocks, footer totals rows, CSV exports (CSV *reading* is supported). Listed as limitations in the dataset card.
- `to_draft` sets `net = gross = Σ line amounts`, `tax = None`. Totals/tax extraction belongs to F12 (week 3). Week 1 metrics are mapping-level.
- MLflow logging (D007) is deferred to week 3, when calibrator versions exist. Week 1 writes to SQLite `eval_runs` only.

---

## File Structure

```
src/invoiceops/
  contract/
    __init__.py        exports Invoice, Line, ChargeType, Refusal, build_contract
    models.py          Pydantic models (spec §2.2)
    build.py           build_contract(draft) -> Invoice | Refusal
  mapping/
    __init__.py        public exports (filled in Task 10)
    text.py            normalize()
    fields.py          TABLE_FIELDS, FIELD_TYPES, REQUIRED_TABLE_FIELDS, CHARGE_LABELS, CHARGE_LOOKUP
    table.py           Table, read_rows, find_header_row, table_from_rows, load_table
    stages.py          build_aliases, AliasStage, FuzzyStage, EmbedStage, default_encoder, infer_kind, type_matrix
    assign.py          assign_greedy, assign_hungarian, pair_margins, gate
    cascade.py         CascadeConfig, MappingResult, Mapper, to_draft
  synth/
    __init__.py
    vocab.py           multilingual headers (last variant = held-out), distractors, banners, currencies
    carriers.py        CarrierSpec, make_carriers, apply_noise, headers_for
    render.py          make_invoice, write_xlsx
    generate.py        split_carriers, check_no_leakage, generate, CLI
  evals/
    __init__.py
    metrics.py         COUNT_KEYS, file_counts, accuracy, false_map_rate, refusal_rate
    bootstrap.py       cluster_bootstrap_ci
    store.py           record_metrics (SQLite eval_runs)
    h1_mapping.py      CONFIGS, tune, run_ablation, render_markdown, CLI
  validation/output_contractor.py   DELETE (replaced by contract/, D011)
tests/
  helpers.py           fake_encoder (deterministic, no model download)
  conftest.py          tiny_dataset fixture
  test_contract.py  test_vocab.py  test_carriers.py  test_render.py  test_generate.py
  test_table.py  test_stages.py  test_assign.py  test_cascade.py
  test_metrics.py  test_bootstrap.py  test_store.py  test_h1_mapping.py  test_embed_real.py (slow)
docs/data/synthetic-v1-card.md
reports/h1_ablation.md  (generated, committed)
```

---

### Task 0: Tooling

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `uv.lock` (generated)

- [ ] **Step 1: Add dependencies**

```bash
uv add pydantic faker openpyxl rapidfuzz numpy scipy sentence-transformers
uv add --dev pytest
```

Expected: `pyproject.toml` gains a filled `dependencies` list and a `[dependency-groups] dev` entry; `uv.lock` created.

- [ ] **Step 2: Add pytest config to `pyproject.toml`** (append at end of file)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: downloads a model or runs a long job"]
addopts = "-m 'not slow'"
```

- [ ] **Step 3: Ignore eval database** — append to `.gitignore`:

```
# Eval history (regenerable)
reports/*.sqlite
```

- [ ] **Step 4: Verify**

Run: `uv run pytest`
Expected: `no tests ran` (exit code 5 is fine at this point).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .gitignore
git commit -m "build: add week 1 dependencies and pytest config" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: Contract package (F1)

**Files:**
- Create: `src/invoiceops/contract/__init__.py`, `src/invoiceops/contract/models.py`, `src/invoiceops/contract/build.py`
- Delete: `src/invoiceops/validation/output_contractor.py`
- Test: `tests/test_contract.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_contract.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.contract'`

- [ ] **Step 3: Implement** — `src/invoiceops/contract/models.py`

```python
"""Canonical invoice contract (system design §2.2). Required fields have no default."""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ChargeType(str, Enum):
    VOICE = "voice"
    SMS = "sms"
    DATA = "data"
    RECURRING = "recurring"
    ONE_OFF = "one_off"
    OTHER = "other"


class Line(BaseModel):
    charge_type: ChargeType
    amount: Decimal
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    description: str | None = None


class Invoice(BaseModel):
    invoice_no: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    invoice_date: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period_start: date | None = None
    period_end: date | None = None
    net: Decimal
    tax: Decimal | None = None
    gross: Decimal
    lines: list[Line] = Field(min_length=1)


class Refusal(BaseModel):
    reason: str
    missing: list[str] = []
```

`src/invoiceops/contract/build.py`

```python
"""Build the canonical contract from a draft dict, or refuse with a reason. Never raises on bad data."""

from decimal import Decimal

from pydantic import ValidationError

from invoiceops.contract.models import Invoice, Refusal

REQUIRED_INVOICE = ("invoice_no", "supplier_id", "invoice_date", "currency", "net", "gross", "lines")
REQUIRED_LINE = ("charge_type", "amount")


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def build_contract(draft: dict) -> Invoice | Refusal:
    missing = [f for f in REQUIRED_INVOICE if _missing(draft.get(f))]
    for i, line in enumerate(draft.get("lines") or []):
        missing += [f"lines[{i}].{f}" for f in REQUIRED_LINE if _missing(line.get(f))]
    if missing:
        return Refusal(reason="missing_required", missing=missing)

    if _missing(draft.get("tax")) and Decimal(str(draft["gross"])) != Decimal(str(draft["net"])):
        return Refusal(reason="tax_missing_and_gross_ne_net", missing=["tax"])

    try:
        return Invoice.model_validate(draft)
    except ValidationError as e:
        fields = sorted({".".join(str(p) for p in err["loc"]) for err in e.errors()})
        return Refusal(reason="invalid", missing=fields)
```

`src/invoiceops/contract/__init__.py`

```python
from invoiceops.contract.build import build_contract
from invoiceops.contract.models import ChargeType, Invoice, Line, Refusal

__all__ = ["ChargeType", "Invoice", "Line", "Refusal", "build_contract"]
```

Delete the old model:

```bash
git rm src/invoiceops/validation/output_contractor.py
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_contract.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/contract tests/test_contract.py
git commit -m "feat(contract): canonical Invoice contract with refusal (F1, D011)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Field vocabulary and text normalisation

**Files:**
- Create: `src/invoiceops/mapping/text.py`, `src/invoiceops/mapping/fields.py`, `src/invoiceops/synth/__init__.py` (empty), `src/invoiceops/synth/vocab.py`
- Test: `tests/test_vocab.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_vocab.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.mapping.text'`

- [ ] **Step 3: Implement** — `src/invoiceops/mapping/text.py`

```python
import re
import unicodedata


def normalize(text: object) -> str:
    """Lowercase, strip accents, turn every non-alphanumeric run into one space."""
    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).split())
```

`src/invoiceops/mapping/fields.py`

```python
"""Target fields a carrier spreadsheet column can map to, and their expected value kinds."""

from invoiceops.mapping.text import normalize

FIELD_TYPES: dict[str, str] = {
    "invoice_no": "id",
    "invoice_date": "date",
    "currency": "currency",
    "charge_type": "text",
    "description": "text",
    "quantity": "number",
    "unit_price": "number",
    "amount": "number",
}
TABLE_FIELDS: tuple[str, ...] = tuple(FIELD_TYPES)
REQUIRED_TABLE_FIELDS: tuple[str, ...] = ("invoice_no", "invoice_date", "currency", "charge_type", "amount")

CHARGE_LABELS: dict[str, dict[str, str]] = {
    "voice": {"en": "Voice", "fr": "Voix", "es": "Voz"},
    "sms": {"en": "SMS", "fr": "SMS", "es": "SMS"},
    "data": {"en": "Data", "fr": "Données", "es": "Datos"},
    "recurring": {"en": "Monthly fee", "fr": "Abonnement", "es": "Cuota mensual"},
}
CHARGE_LOOKUP: dict[str, str] = {
    normalize(label): charge for charge, labels in CHARGE_LABELS.items() for label in labels.values()
}
```

`src/invoiceops/synth/__init__.py` — empty file.

`src/invoiceops/synth/vocab.py`

```python
"""Multilingual header vocabulary for the synthetic generator.

The LAST variant of every list is a held-out synonym: only test carriers may use it,
so the alias dictionary built from dev carriers never contains it (scoping §9).
"""

LANGUAGES = ("en", "fr", "es")
CURRENCIES = ("EUR", "USD", "GBP")

HEADERS: dict[str, dict[str, list[str]]] = {
    "invoice_no": {
        "en": ["Invoice No", "Invoice Number", "Inv #", "Bill Ref", "Document No"],
        "fr": ["N° facture", "Numéro de facture", "Réf. facture", "N° pièce"],
        "es": ["N.º factura", "Número de factura", "Ref. factura", "Nº documento"],
    },
    "invoice_date": {
        "en": ["Invoice Date", "Bill Date", "Date Issued", "Doc Date"],
        "fr": ["Date facture", "Date d'émission", "Date pièce"],
        "es": ["Fecha factura", "Fecha de emisión", "Fecha doc."],
    },
    "currency": {
        "en": ["Currency", "Curr", "CCY"],
        "fr": ["Devise", "Monnaie"],
        "es": ["Moneda", "Divisa"],
    },
    "charge_type": {
        "en": ["Charge Type", "Service", "Traffic Type", "Usage Category"],
        "fr": ["Type de charge", "Service", "Type de trafic", "Catégorie"],
        "es": ["Tipo de cargo", "Servicio", "Tipo de tráfico", "Categoría"],
    },
    "description": {
        "en": ["Description", "Details", "Line Description", "Item"],
        "fr": ["Description", "Libellé", "Détail"],
        "es": ["Descripción", "Concepto", "Detalle"],
    },
    "quantity": {
        "en": ["Quantity", "Qty", "Volume", "Units", "Minutes"],
        "fr": ["Quantité", "Qté", "Volume", "Unités"],
        "es": ["Cantidad", "Cant.", "Volumen", "Unidades"],
    },
    "unit_price": {
        "en": ["Unit Price", "Rate", "Price/Unit", "Unit Cost"],
        "fr": ["Prix unitaire", "Tarif", "PU", "Coût unitaire"],
        "es": ["Precio unitario", "Tarifa", "P. unit.", "Coste unitario"],
    },
    "amount": {
        "en": ["Amount", "Line Total", "Charge", "Net Amount", "Inb usage cost"],
        "fr": ["Montant", "Total ligne", "Montant HT", "Coût trafic entrant"],
        "es": ["Importe", "Total línea", "Cargo", "Importe neto"],
    },
}

# (header, value kind). Some are adversarial: "Amount Prev. Period" looks like amount.
DISTRACTORS: dict[str, list[tuple[str, str]]] = {
    "en": [("Destination", "text"), ("Route ID", "id"), ("Account Manager", "text"), ("Tax Rate %", "number"),
           ("Amount Prev. Period", "number"), ("Call Count", "number"), ("Region Code", "id"), ("Internal Ref", "id")],
    "fr": [("Destination", "text"), ("ID route", "id"), ("Gestionnaire", "text"), ("Taux TVA %", "number"),
           ("Montant période préc.", "number"), ("Nb appels", "number"), ("Code région", "id"), ("Réf. interne", "id")],
    "es": [("Destino", "text"), ("ID ruta", "id"), ("Gestor de cuenta", "text"), ("Tipo IVA %", "number"),
           ("Importe periodo ant.", "number"), ("Nº llamadas", "number"), ("Código región", "id"), ("Ref. interna", "id")],
}

BANNERS: dict[str, list[str]] = {
    "en": ["{carrier} — Interconnect invoice statement", "Billing period: {period}"],
    "fr": ["{carrier} — Relevé de facturation interconnexion", "Période : {period}"],
    "es": ["{carrier} — Extracto de facturación de interconexión", "Periodo: {period}"],
}
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_vocab.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/text.py src/invoiceops/mapping/fields.py src/invoiceops/synth tests/test_vocab.py
git commit -m "feat(synth): multilingual field vocabulary with held-out synonyms" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Carrier template specs

**Files:**
- Create: `src/invoiceops/synth/carriers.py`
- Test: `tests/test_carriers.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_carriers.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_carriers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.synth.carriers'`

- [ ] **Step 3: Implement** — `src/invoiceops/synth/carriers.py`

```python
"""Carrier template specs: which columns a carrier uses, how it names them, in what order.

A carrier's FR/EN/ES templates share structure (same column order, same distractors,
same variant index), which is why the split is by carrier, not by template (D011).
"""

import random
from dataclasses import dataclass

from faker import Faker

from invoiceops.mapping.fields import REQUIRED_TABLE_FIELDS, TABLE_FIELDS
from invoiceops.synth.vocab import CURRENCIES, DISTRACTORS, HEADERS

OPTIONAL_FIELDS = tuple(f for f in TABLE_FIELDS if f not in REQUIRED_TABLE_FIELDS)
NOISES = ("none", "upper", "lower", "snake", "currency_suffix", "abbrev")
N_DISTRACTORS = 5
DISTRACTOR_PREFIX = "~"  # not a letter: field names like "description" must never match it


@dataclass
class CarrierSpec:
    carrier_id: str
    name: str
    currency: str
    tax_rate: str
    fields: tuple[str, ...]
    variant: dict[str, int]
    distractor_ids: tuple[int, ...]
    column_order: tuple[str, ...]
    n_banner_rows: int
    noise: str
    held_out: bool


def make_carriers(n: int, rng: random.Random, fake: Faker, held_out: frozenset[str] = frozenset()) -> list[CarrierSpec]:
    specs = []
    for k in range(1, n + 1):
        carrier_id = f"C{k:02d}"
        fields = list(REQUIRED_TABLE_FIELDS) + [f for f in OPTIONAL_FIELDS if rng.random() < 0.7]
        order = fields + [f"{DISTRACTOR_PREFIX}{i}" for i in range(N_DISTRACTORS)]
        rng.shuffle(order)
        specs.append(
            CarrierSpec(
                carrier_id=carrier_id,
                name=fake.company(),
                currency=rng.choice(CURRENCIES),
                tax_rate=rng.choice(["0", "0.20"]),
                fields=tuple(fields),
                variant={f: rng.randrange(1000) for f in fields},
                distractor_ids=tuple(rng.sample(range(len(DISTRACTORS["en"])), N_DISTRACTORS)),
                column_order=tuple(order),
                n_banner_rows=rng.randint(0, 3),
                noise=rng.choice(NOISES),
                held_out=carrier_id in held_out,
            )
        )
    return specs


def apply_noise(header: str, noise: str, field: str | None, currency: str) -> str:
    if noise == "upper":
        return header.upper()
    if noise == "lower":
        return header.lower()
    if noise == "snake":
        return header.lower().replace(" ", "_")
    if noise == "currency_suffix" and field in ("amount", "unit_price"):
        return f"{header} ({currency})"
    if noise == "abbrev":
        return " ".join(w[:4] + "." if len(w) > 5 else w for w in header.split())
    return header


def _choose_variant(spec: CarrierSpec, field: str, lang: str) -> str:
    options = HEADERS[field][lang]
    v = spec.variant[field]
    if spec.held_out and v % 2 == 0:
        return options[-1]
    seen = options[:-1]
    return seen[v % len(seen)]


def headers_for(spec: CarrierSpec, lang: str) -> tuple[list[str], list[str | None]]:
    """Header texts in column order, and the true field per column (None = distractor)."""
    headers: list[str] = []
    truth: list[str | None] = []
    for key in spec.column_order:
        if key.startswith(DISTRACTOR_PREFIX):
            text, _ = DISTRACTORS[lang][spec.distractor_ids[int(key[1:])]]
            headers.append(apply_noise(text, spec.noise, None, spec.currency))
            truth.append(None)
        else:
            headers.append(apply_noise(_choose_variant(spec, key, lang), spec.noise, key, spec.currency))
            truth.append(key)
    return headers, truth
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_carriers.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/synth/carriers.py tests/test_carriers.py
git commit -m "feat(synth): seeded carrier template specs with header noise" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Invoice records and XLSX rendering

**Files:**
- Create: `src/invoiceops/synth/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_render.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.synth.render'`

- [ ] **Step 3: Implement** — `src/invoiceops/synth/render.py`

```python
"""Ground-truth invoice records and their rendering as a carrier XLSX file."""

import random
from datetime import date, timedelta
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
    for _ in range(rng.randint(3, 12)):
        charge = rng.choice(sorted(CHARGE_LABELS))
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
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_render.py -v`
Expected: 30 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/synth/render.py tests/test_render.py
git commit -m "feat(synth): ground-truth invoices rendered as carrier XLSX" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Dataset generation, carrier split, leakage check (F2)

**Files:**
- Create: `src/invoiceops/synth/generate.py`, `tests/conftest.py`
- Test: `tests/test_generate.py`

- [ ] **Step 1: Write the fixture and failing tests**

`tests/conftest.py`

```python
import pytest

from invoiceops.synth.generate import generate


@pytest.fixture(scope="session")
def tiny_dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    generate(out, seed=7, n_carriers=5, per_template=2)
    return out
```

`tests/test_generate.py`

```python
import json
import random

import pytest

from invoiceops.synth.generate import check_no_leakage, generate, split_carriers


def test_split_is_60_20_20_and_disjoint():
    ids = [f"C{k:02d}" for k in range(1, 16)]
    split = split_carriers(ids, random.Random(0))
    counts = {s: sum(1 for v in split.values() if v == s) for s in ("dev", "calibration", "test")}
    assert counts == {"dev": 9, "calibration": 3, "test": 3}


def test_leakage_check_raises_on_shared_carrier():
    entries = [{"split": "dev", "carrier_id": "C01"}, {"split": "test", "carrier_id": "C01"}]
    with pytest.raises(ValueError, match="leakage"):
        check_no_leakage(entries)


def test_manifest_counts_and_files(tiny_dataset):
    manifest = json.loads((tiny_dataset / "manifest.json").read_text())
    assert len(manifest["entries"]) == 5 * 3 * 2
    for e in manifest["entries"]:
        assert (tiny_dataset / e["path"]).exists()
        assert e["record"]["supplier_id"] == e["carrier_id"]
    test_carriers = {e["carrier_id"] for e in manifest["entries"] if e["split"] == "test"}
    dev_carriers = {e["carrier_id"] for e in manifest["entries"] if e["split"] == "dev"}
    assert test_carriers and not (test_carriers & dev_carriers)


def test_test_hash_is_deterministic(tmp_path):
    a = generate(tmp_path / "a", seed=11, n_carriers=5, per_template=1)
    b = generate(tmp_path / "b", seed=11, n_carriers=5, per_template=1)
    c = generate(tmp_path / "c", seed=12, n_carriers=5, per_template=1)
    assert a["test_hash"] == b["test_hash"] != c["test_hash"]


def test_discrepancy_rate_is_roughly_15_percent(tmp_path):
    m = generate(tmp_path / "d", seed=3, n_carriers=10, per_template=10)
    rate = sum(e["discrepancy"] for e in m["entries"]) / len(m["entries"])
    assert 0.08 < rate < 0.22
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.synth.generate'`

- [ ] **Step 3: Implement** — `src/invoiceops/synth/generate.py`

```python
"""Generate the synthetic Track A dataset: XLSX files + manifest.json with ground truth and splits.

Usage: uv run python -m invoiceops.synth.generate --out data/synthetic/v1 --seed 20260923
"""

import argparse
import hashlib
import json
import random
from collections import defaultdict
from decimal import Decimal
from itertools import combinations
from pathlib import Path

from faker import Faker

from invoiceops.contract import Invoice
from invoiceops.synth.carriers import make_carriers
from invoiceops.synth.render import make_invoice, write_xlsx
from invoiceops.synth.vocab import LANGUAGES

DISCREPANCY_RATE = 0.15


def split_carriers(ids: list[str], rng: random.Random) -> dict[str, str]:
    """60/20/20 dev/calibration/test by carrier (D011)."""
    ids = sorted(ids)
    rng.shuffle(ids)
    n_test = max(1, round(len(ids) * 0.2))
    n_cal = max(1, round(len(ids) * 0.2))
    split = {c: "test" for c in ids[:n_test]}
    split |= {c: "calibration" for c in ids[n_test : n_test + n_cal]}
    split |= {c: "dev" for c in ids[n_test + n_cal :]}
    return split


def check_no_leakage(entries: list[dict]) -> None:
    carriers: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        carriers[e["split"]].add(e["carrier_id"])
    for a, b in combinations(sorted(carriers), 2):
        overlap = carriers[a] & carriers[b]
        if overlap:
            raise ValueError(f"carrier leakage between {a} and {b}: {sorted(overlap)}")


def expected_cost(net: Decimal, rng: random.Random) -> tuple[Decimal, bool]:
    """Reference cost the buyer expected. ~15% carry a 6-20% discrepancy; the rest are within ±1%."""
    if rng.random() < DISCREPANCY_RATE:
        delta = Decimal(rng.choice([-1, 1])) * Decimal(rng.randint(6, 20)) / 100
        return (net * (1 + delta)).quantize(Decimal("0.01")), True
    delta = Decimal(rng.randint(-100, 100)) / 10000
    return (net * (1 + delta)).quantize(Decimal("0.01")), False


def generate(out: Path, seed: int, n_carriers: int = 30, per_template: int = 10) -> dict:
    out = Path(out)
    rng = random.Random(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)

    split = split_carriers([f"C{k:02d}" for k in range(1, n_carriers + 1)], rng)
    held_out = frozenset(c for c, s in split.items() if s == "test")
    specs = make_carriers(n_carriers, rng, fake, held_out=held_out)

    entries = []
    for spec in specs:
        for lang in LANGUAGES:
            for seq in range(per_template):
                record = make_invoice(spec, lang, rng, fake, seq)
                rel = Path(spec.carrier_id) / lang / f"{record['invoice_no']}.xlsx"
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                meta = write_xlsx(out / rel, spec, lang, record, rng, fake)
                expected_net, discrepancy = expected_cost(record["net"], rng)
                entries.append(
                    {
                        "path": str(rel),
                        "carrier_id": spec.carrier_id,
                        "language": lang,
                        "template_id": f"{spec.carrier_id}-{lang}",
                        "split": split[spec.carrier_id],
                        **meta,
                        "record": Invoice.model_validate(record).model_dump(mode="json"),
                        "expected_net": str(expected_net),
                        "discrepancy": discrepancy,
                    }
                )

    check_no_leakage(entries)
    test_entries = [e for e in entries if e["split"] == "test"]
    manifest = {
        "seed": seed,
        "n_carriers": n_carriers,
        "per_template": per_template,
        "splits": {s: sorted(c for c, v in split.items() if v == s) for s in ("dev", "calibration", "test")},
        "test_hash": hashlib.sha256(json.dumps(test_entries, sort_keys=True).encode()).hexdigest(),
        "entries": entries,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--n-carriers", type=int, default=30)
    p.add_argument("--per-template", type=int, default=10)
    a = p.parse_args(argv)
    m = generate(a.out, a.seed, a.n_carriers, a.per_template)
    print(json.dumps({"files": len(m["entries"]), "splits": m["splits"], "test_hash": m["test_hash"]}, indent=1))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_generate.py -v`
Expected: 5 passed

- [ ] **Step 5: Generate the real dataset**

Run: `uv run python -m invoiceops.synth.generate --out data/synthetic/v1 --seed 20260923`
Expected: JSON with `"files": 900`, 18/6/6 carriers in `splits`, and a 64-hex `test_hash`. Copy the printed `splits` and `test_hash` for Step 6.

- [ ] **Step 6: Write the dataset card** — `docs/data/synthetic-v1-card.md`. Paste the values printed in Step 5 into the two marked lines (`Split` and `Test hash`); everything else is literal.

```markdown
# Dataset Card — Synthetic Carrier Spreadsheets v1

**Purpose:** Track A (column mapping) dev, calibration, and frozen test data. Fully synthetic; no private data (scoping §8).
**Regenerate:** `uv run python -m invoiceops.synth.generate --out data/synthetic/v1 --seed 20260923`
**Size:** 30 carriers × 3 languages (EN/FR/ES) × 10 invoices = 900 XLSX files.
**Split (by carrier, D011):** dev 18 / calibration 6 / test 6 — carriers: <paste "splits" from the generator output>
**Test hash (SHA-256 of test manifest entries):** <paste "test_hash" from the generator output>

## Ground truth per file (`manifest.json`)
- `header_row`, `headers`, `mapping` (true field per column; `null` = distractor)
- `record`: canonical `Invoice` (contract §2.2), JSON mode
- `expected_net` and `discrepancy` (15% of invoices off by 6–20%)

## Realism (grounded in thesis audit findings)
- Multilingual header synonyms, 2–5 per field per language
- Header noise per carrier: upper/lower case, snake_case, currency suffix, abbreviation
- 0–3 banner rows above the header
- 5 distractor columns per template, including adversarial look-alikes ("Amount Prev. Period")
- Optional fields (description, quantity, unit_price) present with p = 0.7

## Held-out synonyms
The last synonym of every field/language is used only by **test** carriers (~50% of their fields). The alias dictionary is built from dev carriers only, so the test set measures generalisation to unseen header names.

## Limitations
- Not modelled in v1: pivot blocks, footer totals rows, CSV exports, merged cells, numbers stored as text.
- Structure is shared across a carrier's three languages by design (hence the carrier split).
- Synthetic data can be easier than real carrier files; results are reported as such.
```

- [ ] **Step 7: Commit**

```bash
git add src/invoiceops/synth/generate.py tests/conftest.py tests/test_generate.py docs/data/synthetic-v1-card.md
git commit -m "feat(synth): dataset generator with carrier split, leakage check, dataset card (F2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Table reading and header-row recovery

**Files:**
- Create: `src/invoiceops/mapping/table.py`
- Test: `tests/test_table.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_table.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_table.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.mapping.table'`

- [ ] **Step 3: Implement** — `src/invoiceops/mapping/table.py`

```python
"""Read XLSX/CSV into rows and recover the header row below any banner rows."""

import csv
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook


@dataclass
class Table:
    header_row: int
    headers: list[str]
    rows: list[list[object]]

    def column(self, i: int) -> list[object]:
        return [r[i] if i < len(r) else None for r in self.rows]


def _blank(cell: object) -> bool:
    return cell is None or (isinstance(cell, str) and not cell.strip())


def _is_number(cell: object) -> bool:
    return isinstance(cell, (int, float)) and not isinstance(cell, bool)


def _coerce(cell: str) -> object:
    if not cell.strip():
        return None
    try:
        return float(cell)
    except ValueError:
        return cell


def read_rows(path: Path) -> list[list[object]]:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            return [[_coerce(c) for c in row] for row in csv.reader(f)]
    ws = load_workbook(path, data_only=True).active
    return [list(r) for r in ws.iter_rows(values_only=True)]


def find_header_row(rows: list[list[object]], max_scan: int = 15) -> int:
    """First row with >= 3 non-blank cells, all text, followed by a row containing a number."""
    for i, row in enumerate(rows[:max_scan]):
        cells = [c for c in row if not _blank(c)]
        if len(cells) < 3 or not all(isinstance(c, str) for c in cells):
            continue
        following = rows[i + 1] if i + 1 < len(rows) else []
        if any(_is_number(c) for c in following):
            return i
    raise ValueError(f"no header row found in the first {max_scan} rows")


def table_from_rows(rows: list[list[object]]) -> Table:
    h = find_header_row(rows)
    width = len(rows[h])
    headers = ["" if _blank(c) else str(c).strip() for c in rows[h]]
    body = []
    for r in rows[h + 1 :]:
        if all(_blank(c) for c in r):
            break
        body.append(list(r) + [None] * (width - len(r)))
    return Table(header_row=h, headers=headers, rows=body)


def load_table(path: Path) -> Table:
    return table_from_rows(read_rows(path))
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_table.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/table.py tests/test_table.py
git commit -m "feat(mapping): table reading and header-row recovery" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Alias and fuzzy stages (baselines B0, B1 — F3)

**Files:**
- Create: `src/invoiceops/mapping/stages.py`
- Test: `tests/test_stages.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_stages.py`

```python
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
    assert S[1, 1] == 1.0
    assert S[2].max() < 0.7
    assert np.all((S >= 0) & (S <= 1))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_stages.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.mapping.stages'`

- [ ] **Step 3: Implement** — `src/invoiceops/mapping/stages.py`

```python
"""Scoring stages. Each returns a (n_columns, n_fields) matrix of scores in [0, 1]."""

from collections.abc import Iterable

import numpy as np
from rapidfuzz import fuzz

from invoiceops.mapping.table import Table
from invoiceops.mapping.text import normalize

Aliases = dict[str, set[str]]


def build_aliases(pairs: Iterable[tuple[str, str]], fields: Iterable[str]) -> Aliases:
    """Known header names per field: the field name itself plus headers seen in labelled (dev) data."""
    aliases = {f: {normalize(f.replace("_", " "))} for f in fields}
    for header, field in pairs:
        if field in aliases:
            aliases[field].add(normalize(header))
    return aliases


class AliasStage:
    name = "alias"

    def __init__(self, aliases: Aliases, fields: list[str]):
        self.aliases, self.fields = aliases, list(fields)

    def score(self, table: Table) -> np.ndarray:
        S = np.zeros((len(table.headers), len(self.fields)))
        for i, h in enumerate(table.headers):
            n = normalize(h)
            for j, f in enumerate(self.fields):
                S[i, j] = 1.0 if n in self.aliases[f] else 0.0
        return S


class FuzzyStage:
    name = "fuzzy"

    def __init__(self, aliases: Aliases, fields: list[str]):
        self.aliases, self.fields = aliases, list(fields)

    def score(self, table: Table) -> np.ndarray:
        S = np.zeros((len(table.headers), len(self.fields)))
        for i, h in enumerate(table.headers):
            n = normalize(h)
            for j, f in enumerate(self.fields):
                S[i, j] = max((fuzz.token_set_ratio(n, a) for a in self.aliases[f]), default=0.0) / 100
        return S
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_stages.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/stages.py tests/test_stages.py
git commit -m "feat(mapping): alias and fuzzy scoring stages (B0, B1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Embedding stage and value-type compatibility (F4, part 1)

**Files:**
- Modify: `src/invoiceops/mapping/stages.py` (append)
- Create: `tests/helpers.py`, `tests/test_embed_real.py`
- Modify: `tests/test_stages.py` (append)

- [ ] **Step 1: Write the test helper and failing tests**

`tests/helpers.py`

```python
import zlib

import numpy as np


def fake_encoder(texts: list[str]) -> np.ndarray:
    """Deterministic character-trigram hashing encoder, L2-normalised. No model download."""
    out = np.zeros((len(texts), 64))
    for r, t in enumerate(texts):
        padded = f"  {t} "
        for k in range(len(padded) - 2):
            out[r, zlib.crc32(padded[k : k + 3].encode()) % 64] += 1
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return out / norms
```

Append to `tests/test_stages.py`:

```python
from datetime import datetime

from invoiceops.mapping.stages import EmbedStage, infer_kind, type_matrix
from tests.helpers import fake_encoder


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
```

`tests/test_embed_real.py`

```python
import pytest

from invoiceops.mapping.stages import default_encoder


@pytest.mark.slow
def test_multilingual_model_relates_translations():
    enc = default_encoder()
    v = enc(["montant", "amount", "destination"])
    assert v[0] @ v[1] > v[0] @ v[2]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_stages.py -v`
Expected: FAIL — `ImportError: cannot import name 'EmbedStage'`

- [ ] **Step 3: Implement** — append to `src/invoiceops/mapping/stages.py`

```python
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from invoiceops.mapping.fields import FIELD_TYPES

Encoder = Callable[[list[str]], np.ndarray]  # rows must be L2-normalised
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def default_encoder(model_name: str = DEFAULT_MODEL) -> Encoder:
    from sentence_transformers import SentenceTransformer  # heavy import, only when embeddings are used

    model = SentenceTransformer(model_name)
    return lambda texts: model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True)


class EmbedStage:
    name = "embed"

    def __init__(self, aliases: Aliases, fields: list[str], encoder: Encoder):
        self.fields, self.encoder = list(fields), encoder
        self._cache: dict[str, np.ndarray] = {}
        self._protos = [(j, a) for j, f in enumerate(self.fields) for a in sorted(aliases[f])]
        self._proto_vecs = self._encode([a for _, a in self._protos])

    def _encode(self, texts: list[str]) -> np.ndarray:
        new = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if new:
            for t, v in zip(new, self.encoder(new)):
                self._cache[t] = np.asarray(v)
        return np.stack([self._cache[t] for t in texts])

    def score(self, table: Table) -> np.ndarray:
        sims = self._encode([normalize(h) for h in table.headers]) @ self._proto_vecs.T
        S = np.zeros((len(table.headers), len(self.fields)))
        for k, (j, _) in enumerate(self._protos):
            S[:, j] = np.maximum(S[:, j], sims[:, k])
        return np.clip(S, 0.0, 1.0)


def infer_kind(values: list[object]) -> str:
    vals = [v for v in values if v is not None and not (isinstance(v, str) and not v.strip())]
    if not vals:
        return "empty"
    if all(isinstance(v, (datetime, date)) for v in vals):
        return "date"
    if all(isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in vals):
        return "number"
    strs = [str(v).strip() for v in vals]
    if all(re.fullmatch(r"[A-Z]{3}", s) for s in strs):
        return "currency"
    if all(re.search(r"\d", s) and " " not in s for s in strs):
        return "id"
    return "text"


PARTIAL_COMPAT = {("id", "text"): 0.5, ("text", "id"): 0.5}
MISMATCH = 0.1


def type_matrix(table: Table, fields: list[str]) -> np.ndarray:
    """Multiplier in [0, 1]: 1 if the column's value kind matches the field's expected kind."""
    kinds = [infer_kind(table.column(i)) for i in range(len(table.headers))]
    M = np.empty((len(kinds), len(fields)))
    for i, kind in enumerate(kinds):
        for j, f in enumerate(fields):
            expected = FIELD_TYPES[f]
            M[i, j] = 1.0 if kind == expected else PARTIAL_COMPAT.get((kind, expected), MISMATCH)
    return M
```

Move the new imports (`re`, `Callable`, `date`, `datetime`, `Decimal`, `FIELD_TYPES`) to the top of the file with the existing imports.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_stages.py -v`
Expected: 6 passed

Run once (downloads ~470 MB): `uv run pytest tests/test_embed_real.py -m slow -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/stages.py tests/helpers.py tests/test_stages.py tests/test_embed_real.py
git commit -m "feat(mapping): multilingual embedding stage and value-type compatibility" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Assignment, margins, gate (F4, part 2)

**Files:**
- Create: `src/invoiceops/mapping/assign.py`
- Test: `tests/test_assign.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_assign.py`

```python
import numpy as np
import pytest

from invoiceops.mapping.assign import assign_greedy, assign_hungarian, gate, pair_margins

S = np.array([[0.9, 0.1], [0.8, 0.2], [0.1, 0.7]])


def test_greedy_allows_two_columns_on_one_field():
    assert assign_greedy(S) == {0: 0, 1: 0, 2: 1}


def test_hungarian_is_one_to_one():
    pairs = assign_hungarian(S)
    assert pairs == {0: 0, 2: 1}
    assert len(set(pairs.values())) == len(pairs)


def test_margin_is_min_of_row_and_column_competition():
    m = pair_margins(S, {0: 0, 2: 1})
    assert m[0] == pytest.approx(0.1)  # column 1 competes for field 0 at 0.8
    assert m[2] == pytest.approx(0.5)  # best competitor 0.2


def test_gate_drops_low_score_or_low_margin():
    assert gate(S, {0: 0, 2: 1}, tau=0.5, margin=0.2) == {2: 1}
    assert gate(S, {0: 0, 2: 1}, tau=0.8, margin=0.0) == {0: 0}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_assign.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.mapping.assign'`

- [ ] **Step 3: Implement** — `src/invoiceops/mapping/assign.py`

```python
"""Column → field assignment. Pairs are {column_index: field_index}."""

import numpy as np
from scipy.optimize import linear_sum_assignment


def assign_greedy(S: np.ndarray) -> dict[int, int]:
    """Each column takes its best field. Two columns may take the same field (the failure H1 tests)."""
    return {i: int(S[i].argmax()) for i in range(S.shape[0])}


def assign_hungarian(S: np.ndarray) -> dict[int, int]:
    """One-to-one assignment maximising the total score."""
    rows, cols = linear_sum_assignment(S, maximize=True)
    return {int(i): int(j) for i, j in zip(rows, cols)}


def pair_margins(S: np.ndarray, pairs: dict[int, int]) -> dict[int, float]:
    """Score minus the best competitor: other fields for this column, or other columns for this field."""
    out = {}
    for i, j in pairs.items():
        row_others = np.delete(S[i], j)
        col_others = np.delete(S[:, j], i)
        best_other = max(row_others.max(initial=0.0), col_others.max(initial=0.0))
        out[i] = float(S[i, j] - best_other)
    return out


def gate(S: np.ndarray, pairs: dict[int, int], tau: float, margin: float) -> dict[int, int]:
    """Keep a pair only if its score >= tau and its margin >= margin; the rest stay unmapped."""
    margins = pair_margins(S, pairs)
    return {i: j for i, j in pairs.items() if S[i, j] >= tau and margins[i] >= margin}
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_assign.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/assign.py tests/test_assign.py
git commit -m "feat(mapping): greedy and Hungarian assignment with margin gate" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Mapper and draft builder

**Files:**
- Create: `src/invoiceops/mapping/cascade.py`
- Modify: `src/invoiceops/mapping/__init__.py`
- Test: `tests/test_cascade.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_cascade.py`

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cascade.py -v`
Expected: FAIL — `ImportError: cannot import name 'CascadeConfig' from 'invoiceops.mapping'`

- [ ] **Step 3: Implement** — `src/invoiceops/mapping/cascade.py`

```python
"""Column-mapping cascade: score stages → combine → assign → gate → MappingResult → contract draft."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from invoiceops.mapping.assign import assign_greedy, assign_hungarian, gate, pair_margins
from invoiceops.mapping.fields import CHARGE_LOOKUP, REQUIRED_TABLE_FIELDS, TABLE_FIELDS
from invoiceops.mapping.stages import AliasStage, Aliases, EmbedStage, Encoder, FuzzyStage, default_encoder, type_matrix
from invoiceops.mapping.table import Table, load_table
from invoiceops.mapping.text import normalize


@dataclass(frozen=True)
class CascadeConfig:
    name: str
    stages: tuple[str, ...]
    use_types: bool = False
    assignment: str = "hungarian"  # or "greedy"
    tau: float = 0.5
    margin: float = 0.0


class MappingResult(BaseModel):
    header_row: int
    headers: list[str]
    assignments: dict[int, str]
    scores: dict[int, float]
    margins: dict[int, float]
    unmapped_required: list[str]


class Mapper:
    def __init__(self, aliases: Aliases, encoder: Encoder | None = None, fields: tuple[str, ...] = TABLE_FIELDS):
        self.aliases, self.fields = aliases, list(fields)
        self._encoder = encoder
        self._stages: dict[str, object] = {}

    def _stage(self, name: str):
        if name not in self._stages:
            if name == "alias":
                self._stages[name] = AliasStage(self.aliases, self.fields)
            elif name == "fuzzy":
                self._stages[name] = FuzzyStage(self.aliases, self.fields)
            elif name == "embed":
                self._stages[name] = EmbedStage(self.aliases, self.fields, self._encoder or default_encoder())
            else:
                raise ValueError(f"unknown stage: {name}")
        return self._stages[name]

    def score(self, table: Table, config: CascadeConfig) -> np.ndarray:
        """Mean of enabled stage matrices, times value-type compatibility if enabled."""
        S = np.mean([self._stage(n).score(table) for n in config.stages], axis=0)
        if config.use_types:
            S = S * type_matrix(table, self.fields)
        return S

    def decide(self, table: Table, S: np.ndarray, config: CascadeConfig) -> MappingResult:
        pairs = assign_hungarian(S) if config.assignment == "hungarian" else assign_greedy(S)
        kept = gate(S, pairs, config.tau, config.margin)
        margins = pair_margins(S, kept)
        assignments = {i: self.fields[j] for i, j in kept.items()}
        mapped = set(assignments.values())
        return MappingResult(
            header_row=table.header_row,
            headers=table.headers,
            assignments=assignments,
            scores={i: float(S[i, j]) for i, j in kept.items()},
            margins=margins,
            unmapped_required=[f for f in REQUIRED_TABLE_FIELDS if f not in mapped],
        )

    def map_table(self, path: Path, config: CascadeConfig) -> tuple[Table, MappingResult]:
        table = load_table(path)
        return table, self.decide(table, self.score(table, config), config)


def _text(v: object) -> str | None:
    return None if v is None or not str(v).strip() else str(v).strip()


def _decimal(v: object) -> Decimal | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    try:
        return Decimal(str(v).strip().replace(",", "."))
    except InvalidOperation:
        return None


def _date(v: object) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _charge_type(v: object) -> str | None:
    t = _text(v)
    return None if t is None else CHARGE_LOOKUP.get(normalize(t), "other")


def to_draft(table: Table, result: MappingResult, supplier_id: str) -> dict:
    """Rows → contract draft. If greedy mapped two columns to one field, the higher score wins.

    Totals are the line sum and tax is left empty: totals/tax extraction is F12 (week 3).
    """
    by_field: dict[str, int] = {}
    for i, f in result.assignments.items():
        if f not in by_field or result.scores[i] > result.scores[by_field[f]]:
            by_field[f] = i

    def get(row: list[object], field: str) -> object:
        i = by_field.get(field)
        return None if i is None else row[i]

    lines = [
        {
            "charge_type": _charge_type(get(r, "charge_type")),
            "amount": _decimal(get(r, "amount")),
            "quantity": _decimal(get(r, "quantity")),
            "unit_price": _decimal(get(r, "unit_price")),
            "description": _text(get(r, "description")),
        }
        for r in table.rows
    ]
    amounts = [line["amount"] for line in lines]
    net = sum(amounts, Decimal(0)) if amounts and None not in amounts else None
    first = table.rows[0] if table.rows else []
    return {
        "invoice_no": _text(get(first, "invoice_no")) if first else None,
        "supplier_id": supplier_id,
        "invoice_date": _date(get(first, "invoice_date")) if first else None,
        "currency": _text(get(first, "currency")) if first else None,
        "net": net,
        "tax": None,
        "gross": net,
        "lines": lines,
    }
```

`src/invoiceops/mapping/__init__.py`

```python
from invoiceops.mapping.cascade import CascadeConfig, Mapper, MappingResult, to_draft
from invoiceops.mapping.stages import build_aliases
from invoiceops.mapping.table import Table, load_table, table_from_rows

__all__ = ["CascadeConfig", "Mapper", "MappingResult", "Table", "build_aliases", "load_table", "table_from_rows", "to_draft"]
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest -v`
Expected: all tests pass (slow test deselected)

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/mapping/cascade.py src/invoiceops/mapping/__init__.py tests/test_cascade.py
git commit -m "feat(mapping): Mapper cascade and contract draft builder (F4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Metrics, clustered bootstrap, eval store

**Files:**
- Create: `src/invoiceops/evals/__init__.py` (empty), `src/invoiceops/evals/metrics.py`, `src/invoiceops/evals/bootstrap.py`, `src/invoiceops/evals/store.py`
- Test: `tests/test_metrics.py`, `tests/test_bootstrap.py`, `tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_metrics.py`

```python
from invoiceops.evals.metrics import accuracy, false_map_rate, file_counts, refusal_rate
from invoiceops.mapping import MappingResult

RESULT = MappingResult(
    header_row=0,
    headers=["a", "b", "c"],
    assignments={0: "amount", 1: "currency"},
    scores={0: 1.0, 1: 0.9},
    margins={0: 1.0, 1: 0.5},
    unmapped_required=[],
)
TRUTH = ["amount", None, "currency"]


def test_counts_for_emitted_record_with_a_wrong_map():
    c = file_counts(RESULT, TRUTH, refused=False)
    assert c.tolist() == [1, 2, 1, 2, 1, 0, 1]  # correct, n_target, wrong, n_mapped, silent, refused, n_files
    assert accuracy(c) == 0.5
    assert false_map_rate(c) == 0.5
    assert refusal_rate(c) == 0.0


def test_refused_record_is_never_silent():
    c = file_counts(RESULT, TRUTH, refused=True)
    assert c[4] == 0 and c[5] == 1
```

`tests/test_bootstrap.py`

```python
import numpy as np

from invoiceops.evals.bootstrap import cluster_bootstrap_ci


def ratio(c):
    return c[0] / c[1]


def test_identical_clusters_give_zero_width_ci():
    counts = {k: np.array([[1.0, 2.0]]) for k in "abcde"}
    assert cluster_bootstrap_ci(counts, ratio, n_boot=200, seed=1) == (0.5, 0.5, 0.5)


def test_ci_brackets_point_and_is_deterministic():
    counts = {
        "a": np.array([[1.0, 1.0]]),
        "b": np.array([[0.0, 1.0]]),
        "c": np.array([[1.0, 1.0], [1.0, 1.0]]),
        "d": np.array([[0.0, 1.0]]),
    }
    r1 = cluster_bootstrap_ci(counts, ratio, n_boot=500, seed=3)
    r2 = cluster_bootstrap_ci(counts, ratio, n_boot=500, seed=3)
    assert r1 == r2
    assert r1[0] == 0.6
    assert r1[1] <= r1[0] <= r1[2] and r1[1] < r1[2]
```

`tests/test_store.py`

```python
import sqlite3

from invoiceops.evals.store import record_metrics


def test_record_metrics_appends_rows(tmp_path):
    db = tmp_path / "runs.sqlite"
    record_metrics(db, "run1", "hash", "h1", "B0", {"accuracy": (0.8, 0.7, 0.9), "silent": (0.0, None, None)})
    record_metrics(db, "run2", "hash", "h1", "B0", {"accuracy": (0.85, 0.75, 0.95)})
    with sqlite3.connect(db) as con:
        rows = con.execute("SELECT run_id, metric, value, ci_lo FROM eval_runs ORDER BY run_id, metric").fetchall()
    assert rows == [("run1", "accuracy", 0.8, 0.7), ("run1", "silent", 0.0, None), ("run2", "accuracy", 0.85, 0.75)]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_metrics.py tests/test_bootstrap.py tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.evals.metrics'`

- [ ] **Step 3: Implement**

`src/invoiceops/evals/__init__.py` — empty file.

`src/invoiceops/evals/metrics.py`

```python
"""Per-file mapping counts. Ratios are computed from summed counts, so bootstrap resamples stay exact."""

import numpy as np

from invoiceops.mapping import MappingResult

COUNT_KEYS = ("correct", "n_target", "wrong", "n_mapped", "silent", "refused", "n_files")
CORRECT, N_TARGET, WRONG, N_MAPPED, SILENT, REFUSED, N_FILES = range(len(COUNT_KEYS))


def file_counts(result: MappingResult, truth: list[str | None], refused: bool) -> np.ndarray:
    """A record is silently wrong if it was emitted (not refused) with any wrong column assignment."""
    correct = sum(1 for i, f in result.assignments.items() if truth[i] == f)
    wrong = len(result.assignments) - correct
    n_target = sum(1 for t in truth if t is not None)
    silent = int(not refused and wrong > 0)
    return np.array([correct, n_target, wrong, len(result.assignments), silent, int(refused), 1], dtype=float)


def accuracy(c: np.ndarray) -> float:
    return float(c[CORRECT] / c[N_TARGET]) if c[N_TARGET] else 0.0


def false_map_rate(c: np.ndarray) -> float:
    return float(c[WRONG] / c[N_MAPPED]) if c[N_MAPPED] else 0.0


def refusal_rate(c: np.ndarray) -> float:
    return float(c[REFUSED] / c[N_FILES]) if c[N_FILES] else 0.0
```

`src/invoiceops/evals/bootstrap.py`

```python
"""Cluster bootstrap: resample whole carriers, because invoices of one carrier are not independent."""

from collections.abc import Callable

import numpy as np


def cluster_bootstrap_ci(
    counts_by_cluster: dict[str, np.ndarray],
    stat: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(point, lo, hi). Each cluster maps to an (n_items, k) count array; stat takes a summed (k,) vector."""
    keys = sorted(counts_by_cluster)
    totals = np.stack([np.asarray(counts_by_cluster[k]).sum(axis=0) for k in keys])
    point = float(stat(totals.sum(axis=0)))
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n_boot, len(keys)))
    boots = np.array([stat(totals[i].sum(axis=0)) for i in idx])
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)
```

`src/invoiceops/evals/store.py`

```python
"""Append-only eval history in SQLite (D009)."""

import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT, created_at TEXT, git_sha TEXT, data_hash TEXT,
    component TEXT, config TEXT, metric TEXT, value REAL, ci_lo REAL, ci_hi REAL
)"""


def git_sha() -> str:
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def record_metrics(
    db_path: Path,
    run_id: str,
    data_hash: str,
    component: str,
    config: str,
    metrics: dict[str, tuple[float, float | None, float | None]],
) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    now, sha = datetime.now(timezone.utc).isoformat(), git_sha()
    rows = [(run_id, now, sha, data_hash, component, config, name, v, lo, hi) for name, (v, lo, hi) in metrics.items()]
    with sqlite3.connect(db_path) as con:
        con.execute(SCHEMA)
        con.executemany("INSERT INTO eval_runs VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_metrics.py tests/test_bootstrap.py tests/test_store.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/evals tests/test_metrics.py tests/test_bootstrap.py tests/test_store.py
git commit -m "feat(evals): mapping metrics, carrier-clustered bootstrap, SQLite eval store" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: H1 ablation runner (F5)

**Files:**
- Create: `src/invoiceops/evals/h1_mapping.py`
- Test: `tests/test_h1_mapping.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_h1_mapping.py`

```python
from invoiceops.evals.h1_mapping import CONFIGS, TAUS, render_markdown, run_ablation
from tests.helpers import fake_encoder


def test_run_ablation_on_tiny_dataset(tiny_dataset):
    report = run_ablation(tiny_dataset, encoder=fake_encoder, n_boot=50)
    assert [r.config for r in report.rows] == [c.name for c in CONFIGS]
    for r in report.rows:
        assert 0.0 <= r.accuracy[0] <= 1.0
        assert r.accuracy[1] <= r.accuracy[0] <= r.accuracy[2]
        assert r.tau in TAUS
        assert r.silent >= 0
    assert len(report.h1_diff) == 3
    assert report.n_test_files == 1 * 3 * 2


def test_markdown_has_one_row_per_config_and_verdict(tiny_dataset):
    report = run_ablation(tiny_dataset, encoder=fake_encoder, n_boot=50)
    md = render_markdown(report, git_sha="abc1234")
    assert md.count("\n| ") == len(CONFIGS) + 1  # header row + one per config
    assert "**H1**" in md and ("supported" in md)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_h1_mapping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'invoiceops.evals.h1_mapping'`

- [ ] **Step 3: Implement** — `src/invoiceops/evals/h1_mapping.py`

```python
"""H1 ablation: do embeddings + one-to-one assignment beat fuzzy-only mapping on unseen carriers?

τ and m are tuned per config on dev carriers; all reported numbers come from the frozen test carriers.
Usage: uv run python -m invoiceops.evals.h1_mapping --data data/synthetic/v1
"""

import argparse
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from invoiceops.contract import Refusal, build_contract
from invoiceops.evals.bootstrap import cluster_bootstrap_ci
from invoiceops.evals.metrics import COUNT_KEYS, SILENT, accuracy, false_map_rate, file_counts, refusal_rate
from invoiceops.evals.store import git_sha, record_metrics
from invoiceops.mapping import CascadeConfig, Mapper, Table, build_aliases, load_table, to_draft
from invoiceops.mapping.fields import TABLE_FIELDS
from invoiceops.mapping.stages import Encoder

CONFIGS = (
    CascadeConfig("B0 alias", ("alias",), assignment="greedy"),
    CascadeConfig("B1 +fuzzy", ("alias", "fuzzy"), assignment="greedy"),
    CascadeConfig("S2 +embed", ("alias", "fuzzy", "embed"), assignment="greedy"),
    CascadeConfig("S3 +hungarian", ("alias", "fuzzy", "embed"), assignment="hungarian"),
    CascadeConfig("S4 +value types", ("alias", "fuzzy", "embed"), use_types=True, assignment="hungarian"),
)
BASELINE, CANDIDATE = "B1 +fuzzy", "S3 +hungarian"
TAUS = tuple(round(0.30 + 0.05 * k, 2) for k in range(14))  # 0.30 … 0.95
MARGINS = (0.0, 0.02, 0.05, 0.1, 0.15, 0.2)
MAX_FALSE_MAP = 0.05  # scoping §4
H1_MIN_GAIN = 0.10  # scoping §6

Item = tuple[dict, Table, np.ndarray]
CI = tuple[float, float, float]


@dataclass
class Row:
    config: str
    accuracy: CI
    false_map: CI
    refusal: CI
    silent: int
    tau: float
    margin: float


@dataclass
class Report:
    rows: list[Row]
    h1_diff: CI
    h1_supported: bool
    n_test_carriers: int
    n_test_files: int
    test_hash: str


def prepare(mapper: Mapper, entries: list[dict], data_dir: Path, config: CascadeConfig, tables: dict) -> list[Item]:
    items = []
    for e in entries:
        if e["path"] not in tables:
            tables[e["path"]] = load_table(data_dir / e["path"])
        table = tables[e["path"]]
        items.append((e, table, mapper.score(table, config)))
    return items


def run_config(mapper: Mapper, items: list[Item], config: CascadeConfig) -> dict[str, np.ndarray]:
    per_carrier: dict[str, list[np.ndarray]] = defaultdict(list)
    for e, table, S in items:
        result = mapper.decide(table, S, config)
        refused = isinstance(build_contract(to_draft(table, result, e["carrier_id"])), Refusal)
        per_carrier[e["carrier_id"]].append(file_counts(result, e["mapping"], refused))
    return {k: np.stack(v) for k, v in per_carrier.items()}


def total(counts: dict[str, np.ndarray]) -> np.ndarray:
    return np.sum([c.sum(axis=0) for c in counts.values()], axis=0)


def tune(mapper: Mapper, items: list[Item], config: CascadeConfig) -> CascadeConfig:
    """Best dev accuracy with 0 silent errors and false-map <= 5%; if infeasible, fewest silent errors."""
    best_key, best = None, config
    for tau in TAUS:
        for m in MARGINS:
            cfg = replace(config, tau=tau, margin=m)
            c = total(run_config(mapper, items, cfg))
            feasible = c[SILENT] == 0 and false_map_rate(c) <= MAX_FALSE_MAP
            key = (feasible, accuracy(c) if feasible else -c[SILENT], -false_map_rate(c))
            if best_key is None or key > best_key:
                best_key, best = key, cfg
    return best


def run_ablation(data_dir: Path, encoder: Encoder | None = None, n_boot: int = 2000, seed: int = 0) -> Report:
    data_dir = Path(data_dir)
    manifest = json.loads((data_dir / "manifest.json").read_text())
    dev = [e for e in manifest["entries"] if e["split"] == "dev"]
    test = [e for e in manifest["entries"] if e["split"] == "test"]
    pairs = ((h, f) for e in dev for h, f in zip(e["headers"], e["mapping"]) if f)
    mapper = Mapper(build_aliases(pairs, TABLE_FIELDS), encoder=encoder)

    tables: dict = {}
    rows: list[Row] = []
    test_counts: dict[str, dict[str, np.ndarray]] = {}
    for config in CONFIGS:
        tuned = tune(mapper, prepare(mapper, dev, data_dir, config, tables), config)
        counts = run_config(mapper, prepare(mapper, test, data_dir, config, tables), tuned)
        test_counts[config.name] = counts

        def ci(stat):
            return cluster_bootstrap_ci(counts, stat, n_boot=n_boot, seed=seed)

        rows.append(Row(config.name, ci(accuracy), ci(false_map_rate), ci(refusal_rate),
                        int(total(counts)[SILENT]), tuned.tau, tuned.margin))

    k = len(COUNT_KEYS)
    paired = {
        c: np.concatenate([test_counts[CANDIDATE][c].sum(axis=0), test_counts[BASELINE][c].sum(axis=0)])[None, :]
        for c in test_counts[CANDIDATE]
    }
    diff = cluster_bootstrap_ci(paired, lambda v: accuracy(v[:k]) - accuracy(v[k:]), n_boot=n_boot, seed=seed)
    return Report(
        rows=rows,
        h1_diff=diff,
        h1_supported=diff[0] >= H1_MIN_GAIN and diff[1] > 0,
        n_test_carriers=len({e["carrier_id"] for e in test}),
        n_test_files=len(test),
        test_hash=manifest["test_hash"],
    )


def _fmt(ci: CI) -> str:
    return f"{ci[0]:.3f} [{ci[1]:.3f}, {ci[2]:.3f}]"


def render_markdown(report: Report, git_sha: str) -> str:
    lines = [
        "# H1 — Track A mapping ablation",
        "",
        f"Test set: {report.n_test_files} files from {report.n_test_carriers} unseen carriers · "
        f"test hash `{report.test_hash[:12]}` · commit `{git_sha}`.",
        "95% CIs from a bootstrap clustered by carrier. τ and m tuned on dev carriers only.",
        "",
        "| Config | Accuracy | False-map rate | Refusal rate | Silent errors | τ | m |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report.rows:
        lines.append(f"| {r.config} | {_fmt(r.accuracy)} | {_fmt(r.false_map)} | {_fmt(r.refusal)} "
                     f"| {r.silent} | {r.tau:.2f} | {r.margin:.2f} |")
    d = report.h1_diff
    verdict = "supported" if report.h1_supported else "not supported"
    lines += [
        "",
        f"**H1** ({CANDIDATE} − {BASELINE}, accuracy): {d[0] * 100:+.1f} pts "
        f"[{d[1] * 100:+.1f}, {d[2] * 100:+.1f}] → **{verdict}** (needs ≥ +10 pts and CI excluding 0).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("data/synthetic/v1"))
    p.add_argument("--db", type=Path, default=Path("reports/eval_runs.sqlite"))
    p.add_argument("--out", type=Path, default=Path("reports/h1_ablation.md"))
    p.add_argument("--n-boot", type=int, default=2000)
    a = p.parse_args(argv)

    report = run_ablation(a.data, n_boot=a.n_boot)
    sha = git_sha()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(render_markdown(report, sha))

    run_id = uuid.uuid4().hex[:12]
    for r in report.rows:
        record_metrics(a.db, run_id, report.test_hash, "h1_mapping", r.config, {
            "accuracy": r.accuracy,
            "false_map_rate": r.false_map,
            "refusal_rate": r.refusal,
            "silent_errors": (float(r.silent), None, None),
            "tau": (r.tau, None, None),
            "margin": (r.margin, None, None),
        })
    record_metrics(a.db, run_id, report.test_hash, "h1_mapping", f"{CANDIDATE} - {BASELINE}",
                   {"accuracy_diff": report.h1_diff})
    print(a.out.read_text())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_h1_mapping.py -v`
Expected: 2 passed

Run: `uv run pytest`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/invoiceops/evals/h1_mapping.py tests/test_h1_mapping.py
git commit -m "feat(evals): H1 ablation runner with dev tuning and paired carrier bootstrap (F5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Run the ablation and publish the week 1 result

**Files:**
- Create: `reports/h1_ablation.md` (generated)
- Modify: `README.md`

- [ ] **Step 1: Run the ablation on the real dataset**

Run: `uv run python -m invoiceops.evals.h1_mapping --data data/synthetic/v1`
Expected: prints the Markdown table (5 rows) and the H1 verdict; writes `reports/h1_ablation.md` and appends to `reports/eval_runs.sqlite`. Takes a few minutes (the τ/m grid on dev).

- [ ] **Step 2: Sanity-check the result before publishing**

Check each, and stop to investigate (superpowers:systematic-debugging) if one fails:
- B0 accuracy < 1.0 on test (held-out synonyms must hurt the alias baseline; if B0 = 1.0 the test set is too easy).
- Accuracy is non-decreasing from B0 → B1 in most runs; a large drop signals a scoring bug, not a finding.
- `silent_errors` is reported for every row; if S3/S4 show silent errors > 0, that is a real result — report it, do not retune on test.

Verify the recorded rows:

```bash
sqlite3 reports/eval_runs.sqlite "SELECT config, metric, round(value,3) FROM eval_runs WHERE metric IN ('accuracy','silent_errors') ORDER BY rowid DESC LIMIT 10;"
```

- [ ] **Step 3: Add results to `README.md`** — insert this section after the `## Lifecycle` section, and paste the table and H1 line from `reports/h1_ablation.md` where marked:

```markdown
## Results

### Week 1 — Track A column mapping (H1)

<paste the table and the **H1** line from reports/h1_ablation.md>

Full report: [reports/h1_ablation.md](reports/h1_ablation.md) · Data: [synthetic v1 dataset card](docs/data/synthetic-v1-card.md)
```

- [ ] **Step 4: Commit**

```bash
git add reports/h1_ablation.md README.md
git commit -m "docs: publish week 1 H1 mapping ablation results" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Not in this plan

- **F6 (LLM tie-break, Could):** separate plan only if Task 13 lands before Sat 26 Sep.
- **Calibration split** is generated now but first used in week 3 (F13).
