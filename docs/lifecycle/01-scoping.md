# Phase 1 — Scoping

> Lifecycle: **Scoping** → Data → Modeling → Deployment (+ Monitoring)
> Status: draft v1 · 2026-09-16 · Owner: Said Ibenariba

The goal of scoping is to decide **what problem we solve, how we will know it worked, and what could make the result invalid**, before writing model code. The metrics, targets, and hypotheses below are **pre-registered**: they are fixed now so the results cannot be tuned to look good later.

---

## 1. Problem Statement

Companies that buy services from many suppliers (the reference domain is telecom carrier interconnect billing) must check each supplier invoice against the cost they expect to pay. Today this is largely manual:

- Each supplier uses its own layout and **its own column names** for the same information ("Inb usage cost", "Coût trafic entrant", "Importe"...).
- Per-supplier parsers break when a template changes, and maintaining hundreds of them does not scale.
- Extraction errors are **financial errors**: an unnoticed wrong amount is money over- or under-paid.

Prior research (the author's master's thesis, on a private corpus of 5,382 invoices from 128 carriers) found that **53.8%** of invoices come with a structured spreadsheet and only **7.1%** are scanned. The main problem is therefore **mapping heterogeneous structured data to one schema**, with document vision as the minority path.

> **Relationship to the thesis project.** invoiceops is a separate, from-scratch public rebuild — it shares no infrastructure, code, or data with the private `validation-ai` repo (Orange internship code + PFE master's thesis, confidential). The thesis is used only as a **reference for prior findings** (corpus stats above, the false-map gate in §4, the evaluator-bug lesson in §9) — not as a codebase to extend or research to repeat. Purpose of invoiceops itself: a portfolio piece demonstrating ML deployment/production skills (part of a 30-day public-build sprint), not a continuation of the internship deliverable.

**One sentence:** *Turn heterogeneous supplier invoices into validated, schema-conformant records, and automatically approve only those we are confident are correct.*

## 2. Users and the Decision the System Supports

| | |
|---|---|
| **User** | Billing / accounts-payable reconciliation analyst |
| **Decision per invoice** | `auto_approve` · `human_review` (with reason) · `reject` (contract cannot be built) |
| **Degree of automation** | **Human-in-the-loop → partial automation.** The system assists; a human owns every money decision it is not confident about. Full automation is out of scope. |
| **Cost of errors** | Missed wrong amount (false approve) ≫ unnecessary review (false flag). The threshold is chosen from this asymmetry (Phase 3). |

## 3. Scope

**In scope**
- **Track A (majority path):** XLSX/CSV invoices → header recovery → semantic column mapping → canonical contract (Pydantic) or explicit refusal.
- **Track B (minority path):** PDF/image invoices → header fields (KILE) + line items (LIR) with pretrained models.
- Validation rules: `net + tax = gross`, line sums, currency sanity, variance vs. expected cost > 5%.
- Calibrated confidence → routing decision.
- REST API, CI with evaluation gate, tracing, cloud deployment.
- Review agent (LangGraph + MCP tools, human approval for every write) — **Should** priority, first large item cut on slip.

Feature-level scope, priorities, and interfaces: [system design](../design/system-design.md).

**Out of scope (for this project)**
- Payments, ERP integration, supplier communication.
- Training OCR or document models from scratch. Fine-tuning is a stretch goal only.
- Handwritten or heavily degraded scans.
- Any private or confidential data.

## 4. Success Metrics (three layers)

A model metric only matters if it moves a business metric.

| Layer | Metric | Definition | Target (pre-registered) |
|---|---|---|---|
| **Business** | Straight-through processing (STP) rate | % invoices auto-approved | **≥ 50%** |
| Business | Undetected error rate | % auto-approved invoices containing a wrong field | **≤ 1%** |
| Business | Review load | % invoices sent to human review | report (1 − STP − reject) |
| **System** | Latency p95 | per invoice, Track A / Track B page | **≤ 1 s / ≤ 5 s** (local CPU/Apple Silicon) |
| System | Cost | $ per 1,000 invoices | report |
| **ML — Track A** | Mapping accuracy | correct column → field assignments / all target columns | **≥ 0.90** on unseen templates |
| ML — Track A | False-map rate | distractor or wrong column mapped to a field | **≤ 5%** (thesis gate was 10%) |
| ML — Track A | Silent errors | wrong record emitted without flag or refusal | **0** |
| **ML — Track B** | KILE micro-F1 | field-level F1 after normalisation | report per model; **harness sanity check** within 0.05 of the model card's published score |
| ML — Track B | LIR F1 | line-item (qty, unit price, amount) F1 | report per model |
| ML — Track B | Transfer gap | F1(public benchmark) − F1(FATURA) | flag transfer failure if **> 0.15** |
| **ML — Routing** | Expected calibration error (ECE) | 10-bin ECE on held-out set | **≤ 0.05** after calibration |

## 5. Baselines

Every result is reported against a simple baseline. Improvements without a baseline are not claims.

| Component | Baseline |
|---|---|
| Track A mapping | **B0:** exact alias dictionary · **B1:** fuzzy string matching only |
| Track B extraction | **B0:** OCR text + regex rules |
| Routing | **R0:** send everything to review (STP 0%, undetected 0%) · **R1:** approve everything (STP 100%, undetected = raw error rate) |

## 6. Hypotheses (pre-registered)

| ID | Hypothesis | Test | Supported if |
|---|---|---|---|
| **H1** | Embeddings + constrained one-to-one assignment beat fuzzy-only mapping on **unseen carrier templates** | Paired comparison on the same test templates, bootstrap CI | Improvement ≥ 10 pts, CI excludes 0 |
| **H2** | Public benchmark scores do not transfer to multi-layout invoices | Same harness on CORD/SROIE vs. FATURA | Gap > 0.15 for ≥ 1 model |
| **H3** | Raw confidence scores are miscalibrated, and post-hoc calibration fixes most of it | Reliability diagram + ECE before/after | Raw ECE > 0.10; calibrated ECE reduced ≥ 50% |
| **H4** | A cost-based threshold reaches useful automation safely | STP–error curve on held-out set | STP ≥ 50% at ≤ 1% undetected error |

A hypothesis that is **not supported** is still a valid, reportable result.

## 7. Data Plan (preview of Phase 2)

| Source | Use | Labels | Notes |
|---|---|---|---|
| Synthetic carrier spreadsheets (own generator, seeded) | Track A train/val/test | Ground-truth mapping generated with the data | Realism grounded in thesis audit findings (header diversity, banner rows, pivot blocks, distractors, EN/FR/ES) |
| CORD-v2, SROIE | Track B public benchmark | Public labels | Check licences |
| FATURA | Track B domain-shift test | Public labels | Check licence of the copy used |

**Split rule (leakage guard):** split **by carrier template**, never by row or file. A template seen in training must never appear in test. The test set is **frozen** once generated, with its seed and hash recorded.

## 8. Constraints

- Public and synthetic data only. No artifacts from the author's internship or thesis, and nothing from the private `validation-ai` repo (code, data, private results, Orange data, carrier names) — separate system, prior findings only used as reference (see §1).
- Local-first compute: Apple Silicon laptop, CPU/MPS, Ollama for local models. No paid GPU.
- Time: 4 weeks, ~15 h/week of build time.

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Broken evaluation harness.** A previous benchmark attempt (private repo) produced F1 = 0.0 for nearly every model, most likely an evaluator bug rather than model quality. | All conclusions invalid | Reproduce a published model-card score **before** comparing models; unit-test metrics on hand-made cases |
| Synthetic data too easy → inflated Track A scores | Over-claiming | Noise catalogue, adversarial distractors, held-out template families; state the limitation explicitly |
| Leakage between train and test templates | Inflated scores | Group split by template; automated check that test template IDs ∉ train |
| Compute too small for some models | Incomplete Table 12 | Prefer fewer models with honest numbers; document exclusions in `DECISIONS.md` |
| Dataset licence restrictions | Cannot publish results/data | Check licences in Phase 2; never redistribute raw data |
| Scope creep | Nothing ships | One question per week; cut scope, not days |

## 10. Milestones and Exit Criteria

| Phase | Sprint week | Exit criterion |
|---|---|---|
| 1 · Scoping | Week 0 | This document reviewed; metrics and hypotheses frozen |
| 2 · Data | Week 0–1 | Generator + frozen splits + dataset card; public data loaded; metrics unit-tested |
| 3 · Modeling & evaluation | Week 1–3 | Track A ablation (H1), Table 12 (H2), calibration + routing (H3, H4), error analysis |
| 4 · Deployment & monitoring | Week 4 | API live, CI eval gate blocks a regression, tracing + drift checks |

## 11. Open Questions

- [x] Which canonical fields are **required** for a valid contract vs. optional? → [system design §2.2](../design/system-design.md#22-canonical-contract-resolves-scoping-11-q1)
- [x] What is a realistic cost ratio of a missed error to a review? → 50 : 1 default, sweep 10 : 1 … 200 : 1 ([§2.7](../design/system-design.md#27-decision-rule-resolves-scoping-11-q2-q3))
- [x] Is 5% the right variance tolerance? → 5% **and** > 10 currency units ([§2.7](../design/system-design.md#27-decision-rule-resolves-scoping-11-q2-q3))
