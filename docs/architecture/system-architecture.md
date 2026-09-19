# System Architecture

Module-level component diagram. Maps directly to `src/invoiceops`'s 5 packages (`api`, `extraction`, `mapping`, `routing`, `validation`) — all currently empty skeletons (week 0), so this shows target responsibilities and call direction, not internals.

```mermaid
flowchart TD
    subgraph IFACE["Interface layer"]
        API["REST API<br/>invoice submission,<br/>request/response"]
    end

    subgraph PROC["Processing layer"]
        direction TB
        MAP["mapping<br/>Track A: header recovery +<br/>semantic column mapping"]
        EXTRACT["extraction<br/>Track B: KILE header fields +<br/>LIR line items"]
        VALID["validation<br/>net+tax=gross, line sums,<br/>currency sanity, variance&gt;5%"]
        ROUTE["routing<br/>calibrated confidence to<br/>auto_approve / human_review / reject"]
    end

    subgraph DATAEXT["Data &amp; external"]
        direction TB
        STORE["Storage<br/>synthetic + public datasets<br/>no private corpus"]
        OLLAMA["Ollama<br/>local models<br/>CPU/MPS, Apple Silicon"]
        CI["CI eval gate<br/>blocks regression<br/>DECISIONS.md D002"]
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

    style CI fill:#fff3cd,stroke:#c9a227,stroke-dasharray: 3 3
    style STORE fill:#d4edda,stroke:#2e7d32
    style OLLAMA fill:#d4edda,stroke:#2e7d32
```

## Layers

- **Interface** — the REST API (`src/invoiceops/api`). Receives an invoice, dispatches by file type, returns the routing decision.
- **Processing** — the 4 packages doing the actual work: `mapping` (Track A), `extraction` (Track B), `validation` (shared, both tracks), `routing` (shared, final decision).
- **Data & external** — not a package, but what processing depends on: local model inference (Ollama), the data available to train/test against (see [pipeline-data-flow.md](pipeline-data-flow.md) for why storage is green — public/synthetic only, no private corpus), and the CI evaluation gate that tests processing modules on every change.
