# Architecture Diagrams

Diagrams documenting invoiceops's system design. Status: week 0 — these describe the **target** architecture matching the current package skeleton (`src/invoiceops/{api,extraction,mapping,routing,validation}`), not as-built code.

## Index

- [System Architecture](system-architecture.md) — module-level component diagram: interface, processing, observability, data/external layers, with the concrete tech stack per module.
- [Pipeline & Data Flow](pipeline-data-flow.md) — Track A/B request flow, baselines (`01-scoping.md` §5), and current data-source status (`01-scoping.md` §7).
- [Deployment Topology](deployment-topology.md) — local dev → GitHub Actions CI/CD → cloud runtime, and where tracing plugs in.
- [ML / Data Lifecycle](ml-lifecycle.md) — data → fit/calibrate → eval gate → registry → serve → error analysis loop.

Stack decisions behind every diagram are logged in `DECISIONS.md` (D004-D009).

## Conventions

- Format: [Mermaid](https://mermaid.js.org/), flowchart diagrams.
- Line breaks inside node labels use `<br/>`, not `\n` — the Obsidian Excalidraw plugin's mermaid-to-excalidraw converter doesn't reliably render `\n` inside quoted labels.
- Color legend (used where relevant):
  - 🔴 Red, dashed border — private/off-limits (e.g. the Orange PFE corpus — reference stat only, never used as data)
  - 🟡 Yellow, dashed border — planned, not yet built
  - 🟢 Green, solid border — available now (public data, working component)
