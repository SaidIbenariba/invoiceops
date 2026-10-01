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
    valid_ids = {f"C{k:02d}" for k in range(1, n + 1)}
    unknown = held_out - valid_ids
    if unknown:
        raise ValueError(f"held_out contains unknown carrier ids: {sorted(unknown)}")
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
        return " ".join(w[:5] + "." if len(w) > 6 else w for w in header.split())
    return header


def _choose_variant(spec: CarrierSpec, field: str, lang: str) -> str:
    options = HEADERS[field][lang]
    v = spec.variant[field]
    if spec.held_out and v % 2 == 0:
        return options[-1]
    seen = options[:-1]
    return seen[(v // 2) % len(seen)]


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
