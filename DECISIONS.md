# Decisions

One entry per decision: context, options considered, choice, and why.

## D001 — Structured-first architecture (2026-09-16)

**Context:** In a prior study of 5,382 real carrier invoices, 53.8% came with a structured spreadsheet and only 7.1% were scanned.
**Options:** (a) vision model for every invoice; (b) structured mapping first, vision only when no structured file exists.
**Choice:** (b).
**Why:** Reading a spreadsheet is cheaper, faster, and more accurate than re-extracting the same numbers from pixels. Vision stays as the minority path.

## D002 — Pre-register metrics and hypotheses before modeling (2026-09-16)

**Context:** A previous benchmark attempt produced F1 = 0.0 for nearly every model, most likely an evaluation bug (the commit history shows debugging of label mapping and output parsing).
**Choice:** Freeze metrics, targets, and hypotheses in `docs/lifecycle/01-scoping.md`, and validate the evaluator against a published score before comparing models.
**Why:** Prevents both silent evaluator bugs and tuning targets to the results.

## D003 — Split by carrier template, not by row (2026-09-16)

**Context:** Rows from the same template share header names; a random split leaks them into test.
**Choice:** Group split by template ID; test set frozen with seed and hash.
**Why:** The real task is mapping **unseen** supplier layouts.

## D004 — Single deployable service, not microservices (2026-09-19)

**Context:** 5 packages exist (`api`, `extraction`, `mapping`, `routing`, `validation`); a 4-week, ~15h/week solo budget (§8) can't absorb service-mesh overhead.
**Options:** (a) one process, packages as internal modules; (b) one deployable per package.
**Choice:** (a).
**Why:** No current latency/throughput reason to isolate a module as its own service. Revisit only if a specific p95 target (§4) forces it — logged here if it happens, not guessed now.

## D005 — Track A mapping stack: sentence-transformers + Hungarian algorithm (2026-09-19)

**Context:** H1 claims "embeddings + constrained one-to-one assignment" beats fuzzy-only matching on unseen templates.
**Options:** (a) fuzzy string matching only (already the B1 baseline, not a real choice); (b) embeddings + greedy nearest-match; (c) embeddings + constrained assignment (Hungarian algorithm).
**Choice:** (c) — local `sentence-transformers` embedding model (e.g. `all-MiniLM-L6-v2` or multilingual `e5-small`) + `scipy.optimize.linear_sum_assignment`.
**Why:** Greedy matching can assign two source columns to the same target field; the Hungarian algorithm enforces the one-to-one constraint H1 is actually testing. Zero-shot — no training needed for the baseline; fine-tuning stays a stretch goal per §3.

## D006 — Track B extraction stack: pretrained HF transformers on MPS (2026-09-19)

**Context:** §3 scopes Track B to pretrained KILE (header) + LIR (line-item) models; training/fine-tuning from scratch is explicitly out of scope.
**Choice:** Hugging Face `transformers`, pretrained LayoutLMv3/Donut checkpoints, MPS inference backend (Apple Silicon).
**Why:** Matches the local-first, no-paid-GPU constraint (§8) and the out-of-scope line on training document models from scratch. MPS avoids any cloud GPU cost for inference.
**Amended 2026-09-23:** Model set is now Donut fine-tuned on CORD (specialist), Qwen2.5-VL via Ollama (zero-shot VLM), and Docling text → small LLM (pipeline). LayoutLMv3 is dropped: the base checkpoint has no KIE head, so it would need fine-tuning, which §3 puts out of scope. See `docs/design/system-design.md`.

## D007 — Calibration + experiment tracking: scikit-learn + MLflow (local) (2026-09-19)

**Context:** H3 requires post-hoc calibration reducing ECE to ≤ 0.05; every eval run needs its model version and calibration params traceable, per the D002 evaluator-bug lesson.
**Choice:** `scikit-learn` (Platt scaling / isotonic regression) for calibration; MLflow with a local file-backend for experiment tracking (model revision, calibration params, metrics per run).
**Why:** Both are standard, zero-additional-infra-cost choices at this budget. MLflow specifically ties a metric back to the exact model+calibration version that produced it — without that link, a score regression can't be told apart from a harness bug (D002).

## D008 — Observability split: OpenTelemetry (system) + Langfuse (LLM calls) (2026-09-19)

**Context:** §3 names "tracing" as in-scope. Two different things need tracing: request latency against the ≤1s/≤5s p95 targets (§4), and the Ollama/LLM calls' prompt, cost, and latency.
**Choice:** OpenTelemetry for system-level request tracing; Langfuse layered on top for the LLM-specific calls only.
**Why:** One tool conflating both would either bloat a system trace with prompt payloads or lose LLM-specific detail (token cost, prompt version) inside a generic span. Splitting them keeps each trace readable for what it's actually for.

## D009 — Storage, CI, deployment, dependency management (2026-09-19)

**Context:** Needs: eval-result history, a CI gate blocking regressions (D002), a deploy target for the REST API (§3), and a dependency manager (`pyproject.toml` already declares `uv_build` as the build backend).
**Choice:** SQLite for eval-run/metrics history + filesystem for datasets (`data/public`, `data/synthetic`, already scaffolded); GitHub Actions (test job → eval-gate job → build/deploy job); Docker + Fly.io (or Railway); `uv` for dependency management.
**Why:** All zero/near-zero-cost choices matching the local-first, no-paid-GPU, solo-budget constraints (§8). Postgres, Kubernetes, or a hosted CI runner would be over-provisioned for this scale.
**Amended 2026-09-23:** Deploy target is Azure Container Apps (Azure for Students), fallback Hugging Face Spaces — replaces Fly.io/Railway. A recognised cloud is worth more for the portfolio goal. SQLite confirmed over Postgres: same SQL practice, no service container in CI.

## D010 — Week 1 scope cut after a 2-day slip (2026-09-23)

**Context:** Week 1 started Mon 21 Sep; on Wed 23 Sep the generator was not built. Sprint rule: cut scope, not days.
**Options:** (a) cut inside Week 1; (b) let Week 1 spill into Week 2 and drop a Track B model; (c) slide the sprint 3 days.
**Choice:** (a) — generator reduced from 30 to 15 carriers (still EN/FR/ES); LLM tie-break stage demoted to Could.
**Why:** H1 only needs embeddings + Hungarian vs. fuzzy; the ablation table still ships on 27 Sep and later weeks stay intact.

## D011 — Contract in its own package; split by carrier (2026-09-23)

**Context:** Both tracks produce the canonical invoice and validation, routing, and the API consume it. The generator renders each carrier in 3 languages.
**Choice:** (1) `src/invoiceops/contract/` holds `Invoice`, `Line`, `Refusal`, `build_contract`; it replaces `validation/output_contractor.py`. (2) Refines D003: split by **carrier**, not template, 9 dev / 3 calibration / 3 test.
**Why:** (1) Neither track depends on the other or on validation. (2) FR and EN templates of one carrier share structure; splitting by template would leak it into test.
