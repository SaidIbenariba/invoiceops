# Pipeline & Data Flow

Track A / Track B request flow, baselines, and current data-source status. Source: `docs/lifecycle/01-scoping.md` §3 (Scope), §5 (Baselines), §7 (Data Plan).

```mermaid
flowchart TD
    subgraph DATA["Data sources — Phase 2"]
        direction TB
        PRIV["Orange PFE corpus<br/>5,382 invoices, 128 carriers<br/>PRIVATE — reference stat only<br/>(53.8% structured / 7.1% scanned)<br/>never used as data"]
        SYN["Own synthetic generator<br/>seeded, carrier spreadsheets<br/>NOT YET BUILT"]
        CORD["CORD-v2 (public)<br/>~100 test docs, receipts"]
        SROIE["SROIE (public)<br/>receipts"]
        FATURA["FATURA (public, 3rd-party mirror)<br/>multi-layout invoices<br/>licence: verify"]
    end

    PRIV -.motivates split ratio for.-> SYN

    IN["Supplier invoice arrives"]
    GATE{"Structured file<br/>available?"}
    IN --> GATE
    GATE -->|yes| TA_START
    GATE -->|no| TB_START

    subgraph TA["Track A — majority path"]
        direction TB
        TA_START["XLSX / CSV invoice"] --> TA_HDR["Header recovery"]
        TA_HDR --> TA_MAP["Semantic column mapping<br/>sentence-transformers embeddings +<br/>Hungarian algorithm (scipy)"]
        TA_MAP --> TA_OUT{"Canonical contract<br/>buildable?"}
        TA_OUT -->|yes| TA_CONTRACT["Canonical contract<br/>(Pydantic v2)"]
        TA_OUT -->|no| TA_REFUSE["Explicit refusal"]
        TA_BASE["Baselines<br/>B0: exact alias dict<br/>B1: fuzzy string match"]
        TA_MAP -.compared against.-> TA_BASE
    end
    SYN -.trains/tests.-> TA_MAP

    subgraph TB["Track B — minority path"]
        direction TB
        TB_START["PDF / image invoice"] --> TB_KILE["Header fields (KILE)<br/>Donut-CORD · Qwen2.5-VL (Ollama)<br/>· Docling→LLM"]
        TB_START --> TB_LIR["Line items (LIR)<br/>Donut-CORD · Qwen2.5-VL (Ollama)<br/>· Docling→LLM"]
        TB_BASE["Baseline<br/>B0: OCR text + regex rules"]
        TB_KILE -.compared against.-> TB_BASE
        TB_LIR -.compared against.-> TB_BASE
    end
    CORD -.benchmark.-> TB_KILE
    SROIE -.benchmark.-> TB_KILE
    FATURA -.domain-shift test.-> TB_LIR

    TA_CONTRACT --> VALID
    TB_KILE --> VALID
    TB_LIR --> VALID

    VALID["Validation rules<br/>Pydantic v2"] --> CONF["Calibrated confidence<br/>scikit-learn (Platt / isotonic)<br/>ECE ≤ 0.05 target"]
    CONF --> ROUTE{"Routing decision"}
    ROUTE -->|high confidence| APPROVE["auto_approve"]
    ROUTE -->|low confidence| REVIEW["human_review"]
    TA_REFUSE --> REJECT["reject"]

    style PRIV fill:#f8d7da,stroke:#c62828,stroke-dasharray: 5 5
    style SYN fill:#fff3cd,stroke:#c9a227,stroke-dasharray: 3 3
    style CORD fill:#d4edda,stroke:#2e7d32
    style SROIE fill:#d4edda,stroke:#2e7d32
    style FATURA fill:#d4edda,stroke:#2e7d32
    style TA_BASE fill:#fff3cd,stroke:#c9a227
    style TB_BASE fill:#fff3cd,stroke:#c9a227
    style APPROVE fill:#d4edda,stroke:#2e7d32
    style REVIEW fill:#fde2e1,stroke:#c62828
    style REJECT fill:#e0e0e0,stroke:#616161
```

## Reading the diagram

- **Red, dashed** — the private Orange PFE corpus. Motivates the 53.8%/7.1% split ratio used to justify Track A as the majority path, but is never touched as data (per `01-scoping.md` §8 constraints).
- **Yellow, dashed** — planned but not yet built: the synthetic generator (Track A's only real data source) and the two baseline pairs every result gets compared against.
- **Green** — usable today: the 3 public Track B benchmarks (CORD-v2, SROIE, FATURA).
- Track A currently has **no working data path** — the synthetic generator is the blocker before any Track A number is meaningful.
