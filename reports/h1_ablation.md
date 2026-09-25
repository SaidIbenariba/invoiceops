# H1 — Track A mapping ablation

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
