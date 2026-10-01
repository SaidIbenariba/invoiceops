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
    if len(ids) < 5:
        raise ValueError(f"need at least 5 carriers to split 60/20/20, got {len(ids)}")
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


def generate(out: Path, seed: int, n_carriers: int = 30, per_template: int = 10, force: bool = False) -> dict:
    out = Path(out)
    existing_xlsx = list(out.rglob("*.xlsx")) if out.exists() else []
    existing_manifest = out / "manifest.json"
    if existing_xlsx or existing_manifest.exists():
        if not force:
            raise FileExistsError(
                f"{out} is not empty (found {len(existing_xlsx)} .xlsx file(s) and/or manifest.json); "
                "pass force=True to regenerate"
            )
        for f in existing_xlsx:
            f.unlink()
        if existing_manifest.exists():
            existing_manifest.unlink()

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
                        "path": rel.as_posix(),
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
    p.add_argument("--force", action="store_true", help="overwrite an existing dataset in --out")
    a = p.parse_args(argv)
    m = generate(a.out, a.seed, a.n_carriers, a.per_template, force=a.force)
    print(json.dumps({"files": len(m["entries"]), "splits": m["splits"], "test_hash": m["test_hash"]}, indent=1))


if __name__ == "__main__":
    main()
