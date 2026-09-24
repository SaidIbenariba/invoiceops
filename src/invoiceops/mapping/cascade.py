"""Column-mapping cascade: score stages → combine → assign → gate → MappingResult → contract draft."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from invoiceops.mapping.assign import assign_greedy, assign_hungarian, gate, pair_margins, regret_margins
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
        if config.assignment == "hungarian":
            pairs = assign_hungarian(S)
            all_margins = regret_margins(S, pairs)  # Hungarian: drop in optimal total if the pair is forbidden
        else:
            pairs = assign_greedy(S)
            all_margins = pair_margins(S, pairs)  # greedy: score minus best row/column competitor
        kept = gate(S, pairs, config.tau, config.margin, all_margins)
        margins = {i: all_margins[i] for i in kept}
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
        # tax/totals extraction is week 3 (F12); until then gross == net always,
        # so build_contract's tax_missing_and_gross_ne_net refusal never fires from this draft.
        "tax": None,
        "gross": net,
        "lines": lines,
    }
