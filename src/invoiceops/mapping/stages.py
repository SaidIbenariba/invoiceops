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
                # token_set_ratio returns 100 whenever one token set is a subset of the other,
                # which would let distractors like "Amount Prev. Period" saturate to 1.0 for "amount".
                S[i, j] = max((fuzz.token_sort_ratio(n, a) for a in self.aliases[f]), default=0.0) / 100
        return S
