# Architecture Diagrams

Diagrams documenting invoiceops's system design. Status: week 0 — these describe the **target** architecture matching the current package skeleton (`src/invoiceops/{api,extraction,mapping,routing,validation}`), not as-built code.

## Index

- [System Architecture](system-architecture.md) — module-level component diagram: interface, processing, data/external layers.
- [Pipeline & Data Flow](pipeline-data-flow.md) — Track A/B request flow, baselines (`01-scoping.md` §5), and current data-source status (`01-scoping.md` §7).

## Conventions

- Format: [Mermaid](https://mermaid.js.org/), flowchart diagrams.
- Line breaks inside node labels use `<br/>`, not `\n` — the Obsidian Excalidraw plugin's mermaid-to-excalidraw converter doesn't reliably render `\n` inside quoted labels.
- Color legend (used where relevant):
  - 🔴 Red, dashed border — private/off-limits (e.g. the Orange PFE corpus — reference stat only, never used as data)
  - 🟡 Yellow, dashed border — planned, not yet built
  - 🟢 Green, solid border — available now (public data, working component)
