# Competitive Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/research/competitive-analysis.md`, a sourced survey of OSS and commercial invoice-processing solutions (4 tiers, ~14 tools) with a feature matrix, gap analysis, prioritization for invoiceops's weeks 1-4 milestones, and a LinkedIn-ready positioning statement.

**Architecture:** Not a code change — a research/writing deliverable. Four independent research passes (one per tier) run as parallel forks with a fixed per-tool output schema, so their results merge into one table mechanically. A final synthesis pass (main thread, not forked) builds the matrix and writes the analysis sections.

**Tech Stack:** Agent tool (`subagent_type: "fork"`) for parallel research with WebSearch/firecrawl; no code, no tests. "No placeholders" here means no unsourced or invented tool specs — every claim needs a URL.

This is not a TDD codebase task. There are no unit tests. "Verification" = checking each tool entry has required fields and a real source URL, and that the matrix has no invented rows.

---

## Reference: per-tool output schema (used verbatim in every fork prompt)

Every fork must return each tool using exactly this template:

```markdown
### <Tool Name>
- **Tier:** <OSS extraction lib | Cloud document-AI API | Commercial AP/invoice SaaS | AP automation platform>
- **Extraction approach:** <rules / classical ML / vision-language model / LLM — 1 sentence>
- **Validation & routing depth:** <1-2 sentences: does it validate arithmetic/fields? confidence-based routing to human review?>
- **Confidence / human-in-the-loop model:** <1-2 sentences>
- **Scope boundary:** <what it explicitly does NOT do — e.g. payments, ERP, training>
- **Pricing model:** <free/OSS | usage-based ($/doc) | seat-based | enterprise-quote — include a number if publicly listed>
- **Matrix row:** structured=<Y/N/Partial> | vision=<Y/N/Partial> | validation=<Y/N/Partial> | confidence-routing=<Y/N/Partial> | api=<Y/N> | oss=<Y/N> | pricing-tier=<free|low|mid|enterprise>
- **Sources:** <bullet list of URLs actually fetched — no source, mark the field "N/A, unverified" instead of guessing>
```

---

### Task 1: Scaffold the output doc

**Files:**
- Create: `docs/research/competitive-analysis.md`

- [ ] **Step 1: Create the directory and file with skeleton headings**

```markdown
# Competitive Analysis — Invoice Processing Solutions

> Input to invoiceops scoping (`docs/lifecycle/01-scoping.md`). Spec: `docs/superpowers/specs/2026-09-18-competitive-analysis-design.md`.
> Status: draft · 2026-09-18

## Overview

<!-- one paragraph: why this scan exists, what it covers -->

## Feature Matrix

<!-- one table, tools x axes, filled in Task 3 -->

## OSS Extraction Libraries

<!-- filled in Task 3 -->

## Cloud Document-AI APIs

<!-- filled in Task 3 -->

## Commercial AP/Invoice SaaS

<!-- filled in Task 3 -->

## AP Automation Platforms

<!-- filled in Task 3 -->

## Gap Analysis

<!-- filled in Task 4 -->

## Prioritization

<!-- filled in Task 4 -->

## Positioning Statement

<!-- filled in Task 4 -->

## Sources

<!-- deduplicated URL list, filled in Task 5 -->
```

- [ ] **Step 2: Commit**

```bash
git add docs/research/competitive-analysis.md
git commit -m "docs: scaffold competitive-analysis doc"
```

---

### Task 2: Run four parallel research forks

**Files:** none (forks return findings as message content; no repo writes in this task)

- [ ] **Step 1: Launch all 4 forks in a single message (4 Agent tool calls, one message, `subagent_type: "fork"`)**

Fork A — OSS extraction libs:

```
Research these 4 open-source invoice/document extraction tools: invoice2data, Docling, Donut (naver-clova-ix/donut), PaddleOCR PP-Structure. If PaddleOCR PP-Structure turns out to be poorly documented for invoice-specific structuring, substitute LayoutLMv3 (state that substitution explicitly).

For each tool, use WebSearch/firecrawl to find its official repo/docs and confirm: what it extracts (OCR text / layout / key-value fields / line items), whether it does any validation or confidence-based routing (most OSS libs won't — say so plainly), and how it's licensed/priced (should be free/OSS, confirm the license).

Context: this feeds a competitive-analysis doc for "invoiceops", a portfolio project that maps heterogeneous supplier invoices to one schema, validates them, and routes by confidence (auto-approve / human review / reject). Purpose: skill demonstration + LinkedIn content for recruiters, so accuracy matters — every claim needs a real source URL.

Output: one entry per tool using EXACTLY this template, nothing else:

### <Tool Name>
- **Tier:** OSS extraction lib
- **Extraction approach:** <rules / classical ML / vision-language model / LLM — 1 sentence>
- **Validation & routing depth:** <1-2 sentences>
- **Confidence / human-in-the-loop model:** <1-2 sentences>
- **Scope boundary:** <what it explicitly does NOT do>
- **Pricing model:** <free/OSS | usage-based | seat-based | enterprise-quote>
- **Matrix row:** structured=<Y/N/Partial> | vision=<Y/N/Partial> | validation=<Y/N/Partial> | confidence-routing=<Y/N/Partial> | api=<Y/N> | oss=<Y/N> | pricing-tier=<free|low|mid|enterprise>
- **Sources:** <URLs actually fetched>

If a field can't be verified from a real source, write "N/A, unverified" — never invent a spec. Report back all 4 entries as markdown, nothing else needed in your summary.
```

Fork B — Cloud document-AI APIs:

```
Research these 3 managed cloud document-AI products for invoice extraction: AWS Textract (AnalyzeExpense API), Google Document AI Invoice Parser, Azure AI Document Intelligence prebuilt-invoice model.

Use WebSearch/firecrawl on each vendor's official docs/pricing pages. Confirm: what fields/line-items each extracts out of the box, whether they offer any validation (arithmetic checks) or confidence scoring per field, and current public pricing (per-page or per-document rate).

Context: this feeds a competitive-analysis doc for "invoiceops", a portfolio project that maps heterogeneous supplier invoices to one schema, validates them, and routes by confidence (auto-approve / human review / reject). Purpose: skill demonstration + LinkedIn content for recruiters, so accuracy matters — every claim needs a real source URL.

Output: one entry per tool using EXACTLY this template, nothing else:

### <Tool Name>
- **Tier:** Cloud document-AI API
- **Extraction approach:** <rules / classical ML / vision-language model / LLM — 1 sentence>
- **Validation & routing depth:** <1-2 sentences>
- **Confidence / human-in-the-loop model:** <1-2 sentences>
- **Scope boundary:** <what it explicitly does NOT do>
- **Pricing model:** <free/OSS | usage-based | seat-based | enterprise-quote — include the real $ figure if public>
- **Matrix row:** structured=<Y/N/Partial> | vision=<Y/N/Partial> | validation=<Y/N/Partial> | confidence-routing=<Y/N/Partial> | api=<Y/N> | oss=<Y/N> | pricing-tier=<free|low|mid|enterprise>
- **Sources:** <URLs actually fetched>

If a field can't be verified from a real source, write "N/A, unverified" — never invent a spec. Report back all 3 entries as markdown, nothing else needed in your summary.
```

Fork C — Commercial AP/invoice SaaS:

```
Research these 4 commercial invoice-capture SaaS products: Rossum, Nanonets, Mindee, Veryfi.

Use WebSearch/firecrawl on each vendor's official site/docs/pricing page. Confirm: their extraction approach (most market themselves as AI/LLM-based), whether they offer built-in validation rules and confidence-based routing/human-review workflows (this is usually their main selling point vs raw OCR), and their pricing model (per-document, tiered plans, or enterprise-quote-only).

Context: this feeds a competitive-analysis doc for "invoiceops", a portfolio project that maps heterogeneous supplier invoices to one schema, validates them, and routes by confidence (auto-approve / human review / reject). Purpose: skill demonstration + LinkedIn content for recruiters, so accuracy matters — every claim needs a real source URL.

Output: one entry per tool using EXACTLY this template, nothing else:

### <Tool Name>
- **Tier:** Commercial AP/invoice SaaS
- **Extraction approach:** <rules / classical ML / vision-language model / LLM — 1 sentence>
- **Validation & routing depth:** <1-2 sentences>
- **Confidence / human-in-the-loop model:** <1-2 sentences>
- **Scope boundary:** <what it explicitly does NOT do — payments? ERP posting? etc.>
- **Pricing model:** <free/OSS | usage-based | seat-based | enterprise-quote — include the real $ figure if public, else say "enterprise-quote-only, no public pricing">
- **Matrix row:** structured=<Y/N/Partial> | vision=<Y/N/Partial> | validation=<Y/N/Partial> | confidence-routing=<Y/N/Partial> | api=<Y/N> | oss=<Y/N> | pricing-tier=<free|low|mid|enterprise>
- **Sources:** <URLs actually fetched>

If a field can't be verified from a real source, write "N/A, unverified" — never invent a spec. Report back all 4 entries as markdown, nothing else needed in your summary.
```

Fork D — AP automation platforms:

```
Research these 4 AP automation / procurement platforms where invoice capture is one module inside a bigger product: Bill.com, Ramp Bill Pay, Coupa, Tipalti.

Use WebSearch/firecrawl on each vendor's official site/docs/pricing page. Confirm: what their invoice-capture module actually does (extraction + validation, or just capture-then-route-to-human), how it fits into the bigger product (approval workflows, payments, ERP sync), and pricing model.

Context: this feeds a competitive-analysis doc for "invoiceops", a portfolio project that maps heterogeneous supplier invoices to one schema, validates them, and routes by confidence (auto-approve / human review / reject) — explicitly OUT of invoiceops's own scope: payments, ERP integration, supplier communication. This tier exists to show where that scope boundary sits in real products. Purpose: skill demonstration + LinkedIn content for recruiters, so accuracy matters — every claim needs a real source URL.

Output: one entry per tool using EXACTLY this template, nothing else:

### <Tool Name>
- **Tier:** AP automation platform
- **Extraction approach:** <rules / classical ML / vision-language model / LLM — 1 sentence>
- **Validation & routing depth:** <1-2 sentences>
- **Confidence / human-in-the-loop model:** <1-2 sentences>
- **Scope boundary:** <what it explicitly does NOT do, and what extra scope it covers beyond extraction — payments/ERP/etc.>
- **Pricing model:** <free/OSS | usage-based | seat-based | enterprise-quote>
- **Matrix row:** structured=<Y/N/Partial> | vision=<Y/N/Partial> | validation=<Y/N/Partial> | confidence-routing=<Y/N/Partial> | api=<Y/N> | oss=<Y/N> | pricing-tier=<free|low|mid|enterprise>
- **Sources:** <URLs actually fetched>

If a field can't be verified from a real source, write "N/A, unverified" — never invent a spec. Report back all 4 entries as markdown, nothing else needed in your summary.
```

- [ ] **Step 2: Wait for all 4 fork completion notifications, do not poll**

Each notification arrives as a separate later message. Do not fabricate results before they land.

- [ ] **Step 3: Save each fork's returned markdown into the matching section of `docs/research/competitive-analysis.md`**

Replace the `<!-- filled in Task 3 -->` placeholder under each of the 4 tier headings (`## OSS Extraction Libraries`, `## Cloud Document-AI APIs`, `## Commercial AP/Invoice SaaS`, `## AP Automation Platforms`) with that tier's fork output, verbatim.

- [ ] **Step 4: Commit**

```bash
git add docs/research/competitive-analysis.md
git commit -m "docs: add per-tier findings from research forks"
```

---

### Task 3: Build the feature matrix

**Files:**
- Modify: `docs/research/competitive-analysis.md` (`## Feature Matrix` section)

- [ ] **Step 1: Extract every tool's "Matrix row" line from the 4 tier sections and assemble one table**

Replace `<!-- one table, tools x axes, filled in Task 3 -->` with:

```markdown
| Tool | Tier | Structured | Vision | Validation | Confidence routing | API | OSS | Pricing tier |
|---|---|---|---|---|---|---|---|---|
| <name> | <tier> | <Y/N/Partial> | <Y/N/Partial> | <Y/N/Partial> | <Y/N/Partial> | <Y/N> | <Y/N> | <free/low/mid/enterprise> |
```

One row per tool (~14 rows), values copied directly from each tool's `**Matrix row:**` line — no re-deriving or guessing.

- [ ] **Step 2: Commit**

```bash
git add docs/research/competitive-analysis.md
git commit -m "docs: add feature matrix"
```

---

### Task 4: Write gap analysis, prioritization, positioning statement

**Files:**
- Modify: `docs/research/competitive-analysis.md`
- Reference (read-only): `docs/lifecycle/01-scoping.md`

- [ ] **Step 1: Read `docs/lifecycle/01-scoping.md` §3 (Scope) and §10 (Milestones)**

Use these as the comparison baseline — every gap-analysis claim should reference a specific line from the matrix, not a general impression.

- [ ] **Step 2: Write `## Gap Analysis` (2-3 paragraphs)**

Cover, using the matrix as evidence:
- What's table-stakes across the surveyed tools (e.g. most do extraction; note the real Y/N split for "Validation" and "Confidence routing" columns).
- What's rare or absent (e.g. calibrated confidence routing with a pre-registered ECE target, a false-map gate, structured-first triage before vision fallback — invoiceops §3/§4 items).
- Where invoiceops's declared out-of-scope items (payments, ERP, supplier comms) map onto real products (the AP-platform tier) — i.e. invoiceops deliberately doesn't compete with that tier.

- [ ] **Step 3: Write `## Prioritization` (bullet list)**

For each milestone in `01-scoping.md` §10 (weeks 0-4), one bullet: keep as-is / adjust / cut, with the matrix evidence that justifies it. No placeholder bullets — every one must cite a specific tool or matrix column.

- [ ] **Step 4: Write `## Positioning Statement` (one paragraph, LinkedIn-ready)**

Ground it directly in the gap analysis — no unsupported superlatives, no claims not backed by a matrix row or source.

- [ ] **Step 5: Commit**

```bash
git add docs/research/competitive-analysis.md
git commit -m "docs: add gap analysis, prioritization, positioning statement"
```

---

### Task 5: Sources list, self-review, final commit

**Files:**
- Modify: `docs/research/competitive-analysis.md`

- [ ] **Step 1: Collect every URL from the 4 tier sections' "Sources" fields, deduplicate, and list under `## Sources`**

Replace `<!-- deduplicated URL list, filled in Task 5 -->` with a flat bullet list of unique URLs.

- [ ] **Step 2: Self-review against the spec (`docs/superpowers/specs/2026-09-18-competitive-analysis-design.md`)**

Check:
- Every one of the ~14 tools has all 7 template fields filled (no tool skipped, no field left as the template placeholder text).
- No field states a spec/number without a source URL backing it, except fields explicitly marked "N/A, unverified".
- Gap analysis and prioritization each reference the matrix, not general impressions.
- §6 (Out of scope) of the spec respected: `01-scoping.md` itself untouched, no private/thesis comparisons anywhere in the doc.

Fix any issues found directly in the file.

- [ ] **Step 3: Final commit**

```bash
git add docs/research/competitive-analysis.md
git commit -m "docs: finalize competitive-analysis with sources and self-review fixes"
```
