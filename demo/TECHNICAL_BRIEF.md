# KinoWeave Studio — Technical Brief (Devin Bots Credits Application)

**Target Audience**: Poke / Devin Engineering Evaluation  
**Repository Candidate**: `KinoWeaveStudio-Showcase`  
**Demo Recording**: `demo/kinoweave-studio-demo.mp4` (`104.20s`, `1280x720`, H.264 `yuv420p`, `30 fps`)  
**Subtitles**: `demo/kinoweave-studio-demo.srt` (16 synchronized English cues)

---

## 1. What KinoWeave Studio Solves

AI-assisted video creation often breaks down when creative iteration collides with operational reliability: duplicate billable API submissions on timeout, silent fallback between models, unverified remote media URLs, and destructive edits to source assets.

KinoWeave Studio addresses this with a **local-first, fail-closed control plane**:

- **Authoring vs. Authority Separation**: Authors and helper agents draft `ContentPlans`, `ShotSpecs`, and `PromptSpecs`; **Python Core** owns immutable `PromptSnapshots`, human review bindings, seven-check `GenerationGates`, single-flight budget reservations, safe downloads, and deterministic `FFmpeg` delivery.
- **Explicit Execution Boundaries**: `DEMO / MOCK` UI mode, `LOCAL CORE` offline/local-TLS acceptance mode, and `LIVE PROVIDER` mode (default disabled, requiring dual-file authorization) are mutually exclusive and surfaced prominently in both API responses and UI banners.

---

## 2. How the Demo Video Was Produced

Every visual in `demo/kinoweave-studio-demo.mp4` comes from authentic project artifacts and live tooling with **zero paid Provider API calls**:

1. **`00:00 – 00:05` (Intro Card)**: System architecture summary and explicit offline/local-TLS honesty disclosure.
2. **`00:05 – 00:58` (Live Desktop Chrome UI Walkthrough)**: Recorded directly from live Vite (`127.0.0.1:5174`) serving the React 18 / TypeScript Studio in Desktop Chrome via Chrome DevTools Protocol (`Page.startScreencast`, 113 compositor frames over 50.78s), covering Projects, Assets, Content Studio, Storyboard Studio, Production Center, Bridge Connection security boundaries, Timeline Studio playback, and QA & Delivery.
3. **`00:58 – 01:30` (Authenticated `LOCAL CORE` Acceptance Captures)**: Real Chrome captures from the repository's `LOCAL CORE` acceptance runs (`ISOLATED_MOCK` / local TLS + real Bridge HTTP + real SQLite + pinned FFmpeg `9.0.2`), illustrating 7-check Generation Gate `PASS`, fail-closed `DENIED` (`REVIEW_NOT_FOUND`), `UNKNOWN` non-retry reconciliation state, multi-track `V1/A1` timeline revisions, and decoded H.264/AAC SMPTE export playback with SHA-256 verification.
4. **`01:30 – 01:44` (Verification & Devin Bots Parallel Roadmap)**: Live `2026-11-20` test/build counts strictly separated from the frozen `724f79b` full-regression baseline, followed by the 5 scoped Devin Bots engineering workstreams.

---

## 3. Why Devin Bots Fit This Codebase

- **Clean Interface Boundaries**: Python Core services (`src/kinoweave/`), `h11` loopback Bridge (`src/kinoweave_bridge/`), and React Studio workspaces (`apps/studio-ui/`) communicate through versioned Pydantic schemas, OpenAPI specs, and Zod validators.
- **Dense Deterministic Feedback Loops**: `pytest`, `Vitest`, `tsc`, and `Playwright` provide immediate offline pass/fail signals for autonomous agents without spending external API credits.
- **Five Disjoint Workstreams**: Multi-provider contract validation, async recovery/reconciliation tooling, OpenAPI/Zod parity tests, client-side timeline snapping/waveforms, and headless CI packaging can execute concurrently with minimal file overlap (see `docs/DEVIN_BOTS_ROADMAP.md`).
