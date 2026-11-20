# Manual Screen Recording & Narration Script (90–120s Fallback / Live Re-Recording Guide)

While `demo/kinoweave-studio-demo.mp4` (`104.20s`) was generated automatically via live Desktop Chrome CDP screencast + verified `LOCAL CORE` Chrome acceptance captures + pinned FFmpeg `9.0.2`, this script enables anyone to manually re-record or narrate the exact same 90–120 second demo against a local checkout without modifying production data or calling paid AI APIs.

---

## Pre-Recording Safety Checklist

- [ ] Confirm **zero paid provider credentials** (`HUOSHEN_API_KEY`, `PIXSTAG_API_KEY`, `ARK_API_KEY`, `OPENAI_API_KEY`) are exported in the recording shell.
- [ ] Confirm **zero private data roots** are mounted; use only the React Studio `DEMO / MOCK` mode or a disposable `%TEMP%` offline fixture.
- [ ] Close any terminal windows displaying one-use pairing secrets, personal user directories, or internal hosts before starting screen capture.
- [ ] Set display/capture resolution to `1280x720` or `1920x1080` at `30 fps`.

---

## Launch Commands (Offline / Zero-Cost)

### Terminal 1 — Start UI in `DEMO / MOCK` Mode (No Bridge / No DB)

```powershell
Set-Location <REPO_ROOT>/apps/studio-ui
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Open `http://127.0.0.1:5174/projects` in Desktop Chrome.

### Optional Terminal 2 — Isolated Offline Video Acceptance Fixture (When `core_identity.json` matches working tree)

```powershell
Set-Location <REPO_ROOT>
.venv\Scripts\python.exe -I -B scripts/video_production_fixture.py --prepare-only "$env:TEMP/kw-offline-demo"
./scripts/dev.ps1 -DataRoot "$env:TEMP/kw-offline-demo/studio" -Project n-project `
    -IsolatedMockRoot "$env:TEMP/kw-offline-demo" `
    -VideoOfflineConfig "$env:TEMP/kw-offline-demo/offline-video.json"
```

*(Note: Never record the terminal printing the one-use pairing secret; pair in Chrome before hitting Record.)*

---

## Shot-by-Shot Timing & Narration Script (~104 Seconds)

| Time | Screen / Action | Spoken Narration (English) |
| --- | --- | --- |
| **0:00 – 0:05** | Title frame or `/projects` overview | *"KinoWeave Studio is a deterministic, local-first control plane for AI video production—separating creative authoring from strict Python Core gates, budgets, and FFmpeg verification."* |
| **0:05 – 0:18** | Click `Orbit: A Small Odyssey` → show Project Dashboard & Creative Brief → click `Browse assets` | *"All six workspaces share a single Project Context. Notice the explicit `MOCK / DEMO` boundary badge—never silently faking Core connectivity. Assets are tracked separately from Core's content-addressed asset store."* |
| **0:18 – 0:30** | Open `Content Studio` → select a shot → switch to `Storyboard Studio` → add a visual component (`AI_GENERATIVE`) | *"Content Studio organizes units, sequences, and shots with immutable revisions. Storyboard Studio binds ShotSpecs and visual routes—AI Generative, Code Graphics, or 3D—per shot component."* |
| **0:30 – 0:42** | Open `Production Center` (`Workflow / DAG` & `Tasks`) → switch to `Connection` settings | *"Production Center tracks task graphs and preflight gates before any job runs. In Connection settings, the loopback Bridge enforces one-use pairing secrets, CSRF tokens, and explicit isolation between `DEMO / MOCK` and `LOCAL CORE`."* |
| **0:42 – 0:58** | Open `Timeline Studio` → select clip → press `Play Demo` / `Pause` → open `QA & Delivery` (`Media QA` tab) | *"Timeline Studio manages multi-track edits, frame timecodes, and revisions non-destructively, while QA & Delivery strictly separates browser checklists from CLI-backed human approvals."* |
| **0:58 – 1:12** | Show `LOCAL CORE` Production Center captures (`05-core-production-gate-pass.png`, `06-core-production-gate-denied.png`, `07-core-production-unknown-reconcile.png`) | *"In authenticated `LOCAL CORE` acceptance runs using isolated mocks and local TLS endpoints, every job passes a seven-check Generation Gate. Unreviewed snapshots fail closed, and ambiguous timeouts enter `UNKNOWN` without risky automatic retries."* |
| **1:12 – 1:30** | Show `LOCAL CORE` Timeline (`09-core-timeline-multitrack.png`) and FFmpeg Delivery (`10-core-delivery-ffmpeg-verified.png`) | *"Once ingested, assets enter rational-FPS timelines with SHA-256 revision locking. Pinned FFmpeg 9.0.2 renders H.264/AAC outputs verified via full-stream decoding and SHA-256 matching."* |
| **1:30 – 1:44** | Show live verification table & 5 parallel Devin Bots tasks | *"Live verification on 2026-11-20 confirms 253 Core tests and 128 Vitest specs passing, building cleanly toward five parallel Devin Bots workstreams across contracts, recovery, OpenAPI parity, timeline UX, and CI automation."* |
