# Devin Bots Engineering Roadmap — 5 Parallel Workstreams

KinoWeave Studio is well-suited for autonomous parallel execution with **Devin Bots** because its Core domain services, Bridge HTTP layer, and React Studio UI have **clean interface boundaries**, **fail-closed invariants**, and **dense automated test suites** (`pytest`, `Vitest`, and `Playwright` Chrome E2E).

All five tasks below are designed with **disjoint module ownership** so multiple Devin Bots can operate in parallel on separate branches/PRs without merge conflicts or paid API calls.

---

## Workstream 1: Multi-Provider Contract Matrix & Normalized Error Taxonomy

- **Goal**: Expand and standardize contract validation, parameter JSON Schemas, and vendor-agnostic error classification across image/video adapters (`OpenAI-compatible / Huoshen`, `Pixstag`, `Volcengine Ark`) while preserving strict `APPROVED` vs. `CANDIDATE` isolation.
- **Target Scope**:
  - `src/kinoweave/model_contracts.py`
  - `src/kinoweave/providers.py`
  - `tests/test_model_contracts.py`
  - `tests/test_providers_templates.py`
- **Concrete Deliverables**:
  1. Unified parameterized contract matrix validator ensuring every `ContractRecord` declares explicit `parameter_schema`, bounded resolution/FPS/duration tables, and non-overlapping operation rules.
  2. Normalized provider error-mapping helper with deterministic unit coverage for `AUTH`, `QUOTA`, `RATE_LIMIT`, `INVALID_INPUT`, `POLICY`, `TIMEOUT`, and `UNKNOWN` outcomes without vendor-specific drift.
  3. Regression tests verifying `CANDIDATE` policies remain blocked unless explicitly accepted and pinned revisions remain immutable.
- **Verification Gate**:
  ```powershell
  .venv/Scripts/python.exe -m pytest tests/test_model_contracts.py tests/test_providers_templates.py tests/test_video_provider_contract.py -q
  ```

---

## Workstream 2: Async Video Recovery & Usage-Ledger Reconciliation Tooling

- **Goal**: Harden deterministic offline recovery and operator reconciliation workflows for `UNKNOWN`, `RECONCILIATION_REQUIRED`, and `DOWNLOAD_CONFLICT` jobs without introducing automatic retries or network calls during cached recovery.
- **Target Scope**:
  - `src/kinoweave/video_recovery.py`
  - `src/kinoweave/video_result_cache.py`
  - `scripts/recover_cached_video.py`
  - `tests/test_video_recovery.py`, `tests/test_video_cache.py`
- **Concrete Deliverables**:
  1. Machine-readable reconciliation report subcommand summarizing stuck/uncertain jobs, attempt states, cache receipt verification status (`DOWNLOADED` / `VERIFICATION_FAILED` / `INGESTION_PENDING`), and budget reservation totals.
  2. Extended fault-injection tests covering partial staging files, receipt hash mismatch rejection, cross-project receipt refusal, and idempotent re-ingestion under mocked socket prohibition.
- **Verification Gate**:
  ```powershell
  .venv/Scripts/python.exe -m pytest tests/test_video_recovery.py tests/test_video_cache.py tests/test_offline_video_runtime.py -q
  ```

---

## Workstream 3: Bridge OpenAPI v1 Parity & Schema Drift Verification

- **Goal**: Eliminate manual drift between Python Bridge routes/DTOs, TypeScript Zod schemas, and the published OpenAPI v1 specification by adding automated contract-parity checks across all 42 Bridge operations.
- **Target Scope**:
  - `src/kinoweave_bridge/contract.py`
  - `src/kinoweave_bridge/registry.py`
  - `docs/bridge/openapi-v1.yaml`
  - `apps/studio-ui/src/backend/bridge/*Contracts.ts`
  - `tests/bridge/test_contract.py`
- **Concrete Deliverables**:
  1. Automated test verifying every `(method, path)` entry in `REGISTRY`, `BUSINESS_REGISTRY`, `PRODUCTION_REGISTRY`, `VIDEO_REGISTRY`, `TIMELINE_REGISTRY`, and `DELIVERY_REGISTRY` exists in `docs/bridge/openapi-v1.yaml` with matching HTTP methods and query/body bounds.
  2. Cross-check verifying Zod schemas in `apps/studio-ui/src/backend/bridge/` cover all error codes and job lifecycle statuses (`QUEUED` through `RECONCILIATION_REQUIRED`).
- **Verification Gate**:
  ```powershell
  .venv/Scripts/python.exe -m pytest tests/bridge/test_contract.py -q
  Set-Location apps/studio-ui && npm run typecheck && npm test
  ```

---

## Workstream 4: Non-Destructive Timeline UX (Snapping, Keyboard Shortcuts & Waveforms)

- **Goal**: Improve editor ergonomics in `CoreTimelinePage` (frame-grid snapping, precision NLE keyboard nudging `J/K/L` or `+/-1f`, track solo/mute feedback, and client-side PCM audio peak visualization) while preserving every Core SHA-256 and non-overlap invariant.
- **Target Scope**:
  - `apps/studio-ui/src/workspaces/timeline/CoreTimelinePage.tsx`
  - `apps/studio-ui/src/workspaces/timeline/coreEditingModel.ts`
  - `apps/studio-ui/tests/coreEditingModel.test.ts`
  - `apps/studio-ui/tests/timeline-model.test.ts`
- **Concrete Deliverables**:
  1. Pure deterministic frame-snap helper (`coreEditingModel.ts`) snapping dragged/trimmed clip boundaries to adjacent clip edges or playhead within a configurable frame threshold, refusing overlaps.
  2. Lightweight client-side audio peak envelope renderer for already-verified audio blobs without mutating source files or issuing extra Bridge requests.
  3. Comprehensive Vitest unit tests covering fractional FPS (`24000/1001`, `30000/1001`), lock guards, and snap edge cases.
- **Verification Gate**:
  ```powershell
  ./scripts/test-frontend.ps1
  ./scripts/build-ui.ps1
  ```

---

## Workstream 5: Reproducible Headless CI Evidence Pack & Core-Identity Verification Gate

- **Goal**: Package a one-command offline CI pipeline that runs backend unit/bridge suites, frontend typecheck/Vitest/build, `core_identity.json` consistency verification (LF + tracked file verification), and headless Chrome offline acceptance, exporting standardized JUnit/JSON summaries.
- **Target Scope**:
  - `scripts/run_offline_tests.py`
  - `scripts/verify_integrity.py`
  - `apps/studio-ui/playwright.product.config.ts`
  - `tests/test_readiness_operations.py`
- **Concrete Deliverables**:
  1. Unified offline CI runner producing structured pass/skip/fail JSON artifacts without requiring external network access or paid API keys.
  2. Pre-commit/CI check detecting CRLF drift in `src/kinoweave` and validating binary-file exclusion in `verify_integrity.py` (fixing the UTF-8 decode edge case when binary test fixtures exist).
  3. Sanitized summary generator validating zero credentials or local user paths appear in exported test evidence.
- **Verification Gate**:
  ```powershell
  .venv/Scripts/python.exe -m pytest tests/test_readiness_operations.py tests/test_backup_restore.py -q
  ./scripts/test-frontend.ps1
  ```

---

## Global Safety Guardrails for All Devin Bots Tasks

1. **Zero Paid API Calls**: Every task must validate against in-memory fakes, local TLS test servers, or offline FFmpeg fixtures.
2. **Fail-Closed Security Preserved**: Bots must never bypass `verify_runtime()`, `GenerationGate`, CSRF/Origin checks, or `WorkspaceWriteGrant` enforcement.
3. **Core Identity Pinning**: Any PR modifying `src/kinoweave/` must explicitly regenerate or verify `src/kinoweave_bridge/core_identity.json` on clean LF source bytes as its final step.
