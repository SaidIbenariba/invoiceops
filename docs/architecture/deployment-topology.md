# Deployment Topology

Local dev → CI/CD → cloud runtime. Source: `01-scoping.md` §3 ("REST API, CI with evaluation gate, tracing, cloud deployment") and §8 (local-first, no paid GPU). Stack choices logged in `DECISIONS.md` D004, D008, D009.

```mermaid
flowchart TD
    subgraph LOCAL["Local dev — Apple Silicon"]
        direction TB
        DEV["Developer machine<br/>CPU / MPS inference<br/>uv-managed environment"]
        OLLAMA_L["Ollama<br/>local LLM fallback"]
        DEV --> OLLAMA_L
    end

    subgraph GH["GitHub"]
        direction TB
        REPO["Repo — main branch"]
        subgraph ACTIONS["GitHub Actions CI/CD"]
            direction TB
            TEST["pytest job"]
            GATE["Eval-gate job<br/>DECISIONS.md D002<br/>blocks merge on regression"]
            BUILD["Docker build"]
            TEST --> GATE --> BUILD
        end
        REPO --> TEST
    end

    DEV -->|git push| REPO

    subgraph CLOUD["Cloud — Azure Container Apps<br/>(fallback: HF Spaces)"]
        direction TB
        APP["invoiceops API container<br/>FastAPI + Uvicorn"]
        DB["SQLite volume<br/>eval-run history"]
        APP --> DB
    end

    BUILD -->|deploy on merge to main| APP

    subgraph OBS["Observability"]
        direction TB
        OTEL["OpenTelemetry<br/>request/latency tracing"]
        LANGFUSE_C["Langfuse<br/>LLM call tracing"]
    end

    APP -.system traces.-> OTEL
    APP -.LLM calls.-> LANGFUSE_C

    style GATE fill:#fff3cd,stroke:#c9a227,stroke-dasharray: 3 3
```

## Notes

- No cloud GPU anywhere in this topology — all model inference (Track A embeddings, Track B extraction, Ollama fallback) runs locally during dev and, in the cloud container, on CPU. This is a direct consequence of `01-scoping.md` §8's "no paid GPU" constraint, not an oversight.
- The eval-gate job (yellow, dashed — same convention as elsewhere in this doc set: enforced but easy to get wrong) is what turns D002's evaluator-bug lesson into an actual CI control, not just a written intention.
- SQLite lives on a volume attached to the single API container — acceptable at this scale (`DECISIONS.md` D009); would need to move to a managed DB only if the service were ever split into multiple instances.
