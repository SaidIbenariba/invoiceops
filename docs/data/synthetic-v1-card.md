# Dataset Card — Synthetic Carrier Spreadsheets v1

**Purpose:** Track A (column mapping) dev, calibration, and frozen test data. Fully synthetic; no private data (scoping §8).
**Regenerate:** `uv run python -m invoiceops.synth.generate --out data/synthetic/v1 --seed 20260923 --force`
**Size:** 30 carriers × 3 languages (EN/FR/ES) × 10 invoices = 900 XLSX files.
**Split (by carrier, D011):** dev 18 / calibration 6 / test 6 — carriers: dev = C01, C02, C07, C08, C10, C11, C12, C14, C16, C17, C19, C20, C22, C24, C25, C26, C29, C30; calibration = C04, C06, C13, C18, C21, C23; test = C03, C05, C09, C15, C27, C28
**Test hash (SHA-256 of test manifest entries, incl. per-file content hash):** 5c318ddb99b94f43d149fc47459cd2d4e030259919f04ac3628bc9aaf6530b35

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
Caveat: some held-out synonyms are close to seen ones ("Détail"~"Details", "Importe neto"⊃"Importe", "Net Amount"⊃"Amount", "Nº documento"~"Document No"); these favour the fuzzy baseline, so H1 is tested conservatively. Hard held-outs: "Inb usage cost", "Coût trafic entrant", "Minutes", "Usage Category".

## Limitations
- Not modelled in v1: pivot blocks, footer totals rows, CSV exports, merged cells, numbers stored as text.
- Structure is shared across a carrier's three languages by design (hence the carrier split).
- Synthetic data can be easier than real carrier files; results are reported as such.
- Abbreviation noise can reduce a single-word header to a stub ("Quantity" → "Quant."), removing most field signal for every stage alike.
- Regeneration is exact only with the locked dependencies (uv.lock: Faker, openpyxl).
