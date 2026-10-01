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
TAUS = tuple(round(0.10 + 0.05 * k, 2) for k in range(18))  # 0.10 … 0.95
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
    """Best dev accuracy with 0 silent errors and false-map <= 5%; if infeasible, fewest silent errors.

    Refusal rate is a secondary criterion (after accuracy, before false-map) among feasible
    configs: STP (straight-through processing) rate is a business metric (scoping.md §4), so
    a config that refuses nearly everything is useless even with 0 silent errors and 0 false
    maps — without this term, ties on (feasible, accuracy) left the tuner indifferent between
    a config that maps everything and one that maps almost nothing.
    """
    best_key, best = None, config
    for tau in TAUS:
        for m in MARGINS:
            cfg = replace(config, tau=tau, margin=m)
            c = total(run_config(mapper, items, cfg))
            feasible = c[SILENT] == 0 and false_map_rate(c) <= MAX_FALSE_MAP
            key = (
                feasible,
                accuracy(c) if feasible else -c[SILENT],
                -refusal_rate(c) if feasible else 0,
                -false_map_rate(c),
            )
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
        "95% CIs from a bootstrap clustered by carrier. τ and m tuned on dev carriers only. "
        "m is a regret margin for Hungarian rows and a best-competitor margin for greedy rows (scales differ).",
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
