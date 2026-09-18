# Design — Competitive Analysis (invoiceops scoping input)

> Status: approved · 2026-09-18 · Owner: Said Ibenariba

## 1. Purpose

invoiceops is a public, from-scratch portfolio build (skill-building in ML/data engineering, and source material for LinkedIn content aimed at recruiters — see `docs/lifecycle/01-scoping.md` §1). Before finalizing scope and milestones, survey what open-source and commercial invoice-processing solutions already do, so scope decisions (§3 and §10 of the scoping doc) are made against the real landscape, not assumptions.

This is a research deliverable, not a code change. Output is a standalone document.

## 2. Deliverable

`docs/research/competitive-analysis.md` — a new file, separate from the numbered `docs/lifecycle/` phase docs (this isn't a lifecycle phase; it's input to Phase 1 scoping).

Skeleton:
1. Overview (what/why, one paragraph)
2. Feature matrix (single table, tools × axes)
3. Per-tier findings (subsection per tier, one entry per tool)
4. Gap analysis
5. Prioritization (maps to `01-scoping.md` §10 milestones)
6. Positioning statement (LinkedIn-ready paragraph)
7. Sources (all URLs cited, deduplicated)

## 3. Scope of the scan

Four tiers, ~14 tools total, shortlist not exhaustive:

| Tier | Tools |
|---|---|
| OSS extraction libs | invoice2data, Docling, Donut, PaddleOCR+PP-Structure (swap for LayoutLMv3 if better-sourced) |
| Cloud document-AI APIs | AWS Textract AnalyzeExpense, Google Document AI Invoice Parser, Azure AI Document Intelligence prebuilt-invoice |
| Commercial AP/invoice SaaS | Rossum, Nanonets, Mindee, Veryfi |
| AP automation platforms | Bill.com, Ramp Bill Pay, Coupa, Tipalti |

Per-tool entry schema:
- Name, category/tier
- Extraction approach (rules / classical ML / vision-language model / LLM)
- Validation & routing depth (does it validate arithmetic, flag low-confidence, route to human review?)
- Confidence / human-in-the-loop model
- Scope boundary (what it explicitly does *not* do — payments, ERP, etc.)
- Pricing model (free/OSS, usage-based, seat-based, enterprise-quote)
- 1-3 sourced citations (URL)

Facts must be live-sourced (WebSearch/firecrawl), not from training-data recall. Unverifiable fields are marked "N/A, unverified" rather than guessed — this doc may be read by recruiters, so it must not misstate a real product's capabilities.

## 4. Execution: parallel forks

Four forks launched in one batch, one per tier. Each fork is briefed with:
- Project context: invoiceops's own scope (Track A structured mapping majority path, Track B document-vision minority path, validation rules, calibrated confidence routing — from `01-scoping.md` §3) and purpose (portfolio/skill-building/LinkedIn).
- Its assigned tier and tool shortlist (table above).
- The per-tool output schema (§3 above).
- Instruction to cite sources and never invent specs.

Rationale for parallel forks over sequential or single-agent delegation: tiers are independent research questions: no fork needs another's findings mid-task. Parallel execution keeps raw search/scrape output out of the main thread's context; only structured, cited findings come back.

## 5. Synthesis (done by main thread, not forked)

Once all four forks return:
1. Build the feature matrix from the four sets of structured findings.
2. Write gap analysis (2-3 paragraphs): what's table-stakes across surveyed tools (OCR/extraction, basic arithmetic validation) vs. what's rare (calibrated confidence routing with a pre-registered ECE target, a false-map gate, structured-first triage before vision) — this is invoiceops's differentiation.
3. Write prioritization: bullets mapping findings to keep/cut/adjust decisions for the weeks 1-4 milestones in `01-scoping.md` §10.
4. Write one short positioning-statement paragraph, usable directly as LinkedIn copy, grounded in the gap analysis (no unsupported superlatives).

## 6. Out of scope (for this deliverable)

- Editing `01-scoping.md` itself — this doc informs it; any resulting scope changes are a separate, explicit follow-up decision.
- Exhaustive market coverage (20+ tools) — shortlist only, per approved research-depth choice.
- Pricing negotiation detail, contract terms, or anything behind a login/paywall.
- Any private/confidential comparison to the author's thesis corpus or findings (per `01-scoping.md` §8 constraints).

## 7. Open questions

None outstanding — tool shortlist, tiers, depth, and output structure were all confirmed during brainstorming.
