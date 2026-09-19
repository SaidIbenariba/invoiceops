# ML / Data Lifecycle

Data → fit/calibrate → eval gate → registry → serve → error analysis. The data-scientist and ML-engineer view: how a model version earns the right to serve traffic. Source: `01-scoping.md` §5-§7, §9; stack choices in `DECISIONS.md` D005-D007.

```mermaid
flowchart LR
    GEN["Synthetic generator<br/>seeded, carrier spreadsheets<br/>NOT YET BUILT"] --> SPLIT
    PUB["Public benchmarks<br/>CORD-v2, SROIE, FATURA<br/>licence-checked"] --> SPLIT

    SPLIT["Group split by template<br/>frozen test set, hash recorded<br/>leakage guard"] --> FIT

    FIT["Fit / calibrate<br/>embeddings: zero-shot<br/>scikit-learn calibration<br/>(Platt / isotonic)"] --> LOG

    LOG["MLflow (local)<br/>log model revision,<br/>calibration params, metrics"] --> EVAL

    EVAL["Eval harness<br/>bootstrap CI (H1)<br/>reliability diagram + ECE (H3)<br/>sanity check vs. model-card score"] --> GATE

    GATE{"CI eval gate<br/>meets frozen targets?<br/>DECISIONS.md D002"}
    GATE -->|no| BLOCK["Block merge<br/>result still reportable<br/>as 'not supported' (§6)"]
    GATE -->|yes| REGISTRY["Model + calibration<br/>version pinned"]

    REGISTRY --> SERVE["Serve<br/>mapping + extraction + routing<br/>in production API"]
    SERVE -.production data.-> ERR["Error analysis<br/>false-maps, silent errors<br/>mandatory before claiming STP"]
    ERR -.informs next.-> GEN

    style GEN fill:#fff3cd,stroke:#c9a227,stroke-dasharray: 3 3
    style BLOCK fill:#f8d7da,stroke:#c62828
    style REGISTRY fill:#d4edda,stroke:#2e7d32
```

## Notes

- **A hypothesis that fails the gate is not a failed project.** `01-scoping.md` §6 explicitly allows "not supported" as a valid, reportable result — `BLOCK` here stops a bad model from merging, it doesn't stop the finding from being written up.
- The loop from error analysis back to the generator is deliberate: false-map and silent-error patterns found in production are exactly the adversarial distractors the synthetic generator (§7) needs to cover, not just a monitoring dead end.
- Nothing in this lifecycle runs without a model version and calibration params logged first (`LOG` before `EVAL`) — this is what makes D002's "reproduce a published score before comparing models" actually enforceable per run, not just a one-time check.
