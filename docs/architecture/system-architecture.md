# System Architecture

Module-level component diagram. Maps to `src/invoiceops`'s packages (`api`, `extraction`, `mapping`, `routing`, `validation`, plus `contract` per D011 — see [system design §3](../design/system-design.md#3-components-and-interfaces) for interfaces) — all currently empty skeletons (week 0), so this shows target responsibilities and call direction, not internals.

```mermaid
flowchart TD
    subgraph IFACE["Interface layer"]
        API["REST API<br/>FastAPI + Uvicorn<br/>invoice submission,<br/>request/response"]
    end

    subgraph PROC["Processing layer"]
        direction TB
        MAP["mapping — Track A<br/>sentence-transformers embeddings +<br/>Hungarian algorithm<br/>(scipy.optimize.linear_sum_assignment)"]
        EXTRACT["extraction — Track B<br/>Donut-CORD · Qwen2.5-VL (Ollama)<br/>· Docling→LLM<br/>KILE header fields + LIR line items"]
        VALID["validation<br/>Pydantic v2 validators<br/>net+tax=gross, line sums,<br/>currency sanity, variance&gt;5%"]
        ROUTE["routing<br/>scikit-learn calibration<br/>(Platt / isotonic) to<br/>auto_approve / human_review / reject"]
    end

    subgraph OBS["Observability &amp; tracking"]
        direction TB
        OTEL["OpenTelemetry<br/>system/request tracing<br/>vs. p95 latency targets"]
        LANGFUSE["Langfuse<br/>LLM call tracing<br/>prompt / cost / latency"]
        MLFLOW["MLflow (local)<br/>model + calibration<br/>version, metrics per run"]
    end

    subgraph DATAEXT["Data &amp; external"]
        direction TB
        STORE["Storage<br/>SQLite (eval results) +<br/>filesystem (data/public, data/synthetic)<br/>no private corpus"]
        OLLAMA["Ollama<br/>local LLM fallback<br/>CPU/MPS, Apple Silicon"]
        CI["CI eval gate<br/>GitHub Actions + pytest<br/>blocks regression<br/>DECISIONS.md D002"]
    end

    API -->|structured file| MAP
    API -->|PDF / image| EXTRACT
    MAP --> VALID
    EXTRACT --> VALID
    VALID --> ROUTE
    ROUTE --> API

    MAP -.uses.-> OLLAMA
    EXTRACT -.uses.-> OLLAMA
    MAP -.reads.-> STORE
    EXTRACT -.reads.-> STORE
    CI -.tests.-> MAP
    CI -.tests.-> EXTRACT
    CI -.tests.-> VALID
    CI -.tests.-> ROUTE

    API -.traced by.-> OTEL
    MAP -.LLM calls traced by.-> LANGFUSE
    EXTRACT -.LLM calls traced by.-> LANGFUSE
    MAP -.logged to.-> MLFLOW
    EXTRACT -.logged to.-> MLFLOW
    ROUTE -.logged to.-> MLFLOW

    style CI fill:#fff3cd,stroke:#c9a227,stroke-dasharray: 3 3
    style STORE fill:#d4edda,stroke:#2e7d32
    style OLLAMA fill:#d4edda,stroke:#2e7d32
```

## Layers

- **Interface** — the REST API (`src/invoiceops/api`), FastAPI + Uvicorn. Receives an invoice, dispatches by file type, returns the routing decision.
- **Processing** — the 4 packages doing the actual work: `mapping` (Track A: embeddings + Hungarian-algorithm assignment), `extraction` (Track B: pretrained HF transformer models on MPS), `validation` (shared, Pydantic validators), `routing` (shared, scikit-learn-calibrated decision).
- **Observability & tracking** — cross-cutting, not a package: OpenTelemetry for system-level request tracing, Langfuse specifically for the LLM/Ollama calls, MLflow for model/calibration versioning tied to every eval run (see `DECISIONS.md` D007-D008 for why these are split).
- **Data & external** — local model inference (Ollama), the data available to train/test against (see [pipeline-data-flow.md](pipeline-data-flow.md) for why storage is green — public/synthetic only, no private corpus), and the CI evaluation gate that tests processing modules on every change.

Stack rationale for every module here is logged in `DECISIONS.md` D004-D009.
