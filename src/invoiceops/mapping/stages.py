"""Scoring stages. Each returns a (n_columns, n_fields) matrix of scores in [0, 1]."""

import re
from collections.abc import Callable, Iterable
from datetime import date, datetime
from decimal import Decimal

import numpy as np
from rapidfuzz import fuzz

from invoiceops.mapping.fields import FIELD_TYPES
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
