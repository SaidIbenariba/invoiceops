# invoiceops

Open invoice validation: map heterogeneous supplier invoices to one schema, extract fields from documents, validate them against business rules, and automatically approve only what the system is confident about.

> Work in progress. Built in public following the ML project lifecycle.

## Lifecycle

| Phase | Document | Status |
|---|---|---|
| 1. Scoping | [docs/lifecycle/01-scoping.md](docs/lifecycle/01-scoping.md) | Draft |
| 2. Data | `docs/lifecycle/02-data.md` | Not started |
| 3. Modeling & evaluation | `docs/lifecycle/03-modeling.md` | Not started |
| 4. Deployment & monitoring | `docs/lifecycle/04-deployment.md` | Not started |

System design, feature backlog, and timeline: [docs/design/system-design.md](docs/design/system-design.md).

Design decisions are logged in [DECISIONS.md](DECISIONS.md).

## Results

### Week 1 — Track A column mapping (H1)

Test set: 180 files from 6 unseen carriers · test hash `5c318ddb99b9` · commit `1dfce5b-dirty`.
95% CIs from a bootstrap clustered by carrier. τ and m tuned on dev carriers only. m is a regret margin for Hungarian rows and a best-competitor margin for greedy rows (scales differ).

| Config | Accuracy | False-map rate | Refusal rate | Silent errors | τ | m |
|---|---|---|---|---|---|---|
| B0 alias | 0.619 [0.500, 0.730] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0 | 0.10 | 0.00 |
| B1 +fuzzy | 0.651 [0.558, 0.744] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0 | 0.10 | 0.10 |
| S2 +embed | 0.667 [0.565, 0.758] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0 | 0.10 | 0.10 |
| S3 +hungarian | 0.698 [0.616, 0.775] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0 | 0.10 | 0.15 |
| S4 +value types | 0.730 [0.667, 0.821] | 0.000 [0.000, 0.000] | 0.778 [0.556, 1.000] | 0 | 0.45 | 0.20 |

**H1** (S3 +hungarian − B1 +fuzzy, accuracy): +4.8 pts [+0.0, +9.6] → **not supported** (needs ≥ +10 pts and CI excluding 0).

Full report: [reports/h1_ablation.md](reports/h1_ablation.md) · Data: [synthetic v1 dataset card](docs/data/synthetic-v1-card.md)

The refusal rate is the headline finding here, not a footnote: every alias/fuzzy/embed/Hungarian config (B0–S3) refuses 100% of the unseen-carrier test files, and even S4 (value-types + Hungarian) still refuses 78% of them. This is a margin problem, not a τ problem — a genuinely correct column (e.g. a short, easily-confused header like a currency code) can score highest for its true field and still get gated out, because another column scores a close second for that same field (pushing the margin to near-zero or negative), or wins the field outright once Hungarian reassignment resolves ties globally. Which specific column contends for the field varies by carrier and file, so we don't name one universal culprit here — a prior draft's claim that a specific header pair was "the" cause didn't reproduce on real files, and we're not repeating it without verification. Framed per the scoping doc's own rule that an unsupported hypothesis is still a valid, reportable result: the fail-safe is working exactly as designed — 0 silent errors across every configuration — and correctly prefers refusing to guessing wrong when a column's mapping is genuinely ambiguous under the current scorer/margin combination. That's a real, current limitation of the fuzzy and embedding stages on short or ambiguous headers, not a bug in the routing logic.

## Data

Only public datasets and seeded synthetic data. Raw data is never committed.
