# Test & Runtime Verification Evidence

This document distinguishes **live checks executed directly on `2026-11-20`** from the **historical frozen baseline (`commit 724f79b`, `2026-11-11`)**. Counts across separate runs and commits are never added together or presented as live production provider validation.

**External Paid API Calls Across All Runs Listed Here**: `0` (Offline mocks, in-memory fakes, and local loopback TLS servers only).

---

## 1. Live Verification Results (`2026-11-20`, Working Tree at `b31e426` + Active Uncommitted Work)

### Environment Verified

| Component | Verified Version / Status |
| --- | --- |
| Python Virtual Environment | `Python 3.12.14` (`pip check`: `No broken requirements found.`) |
| Node.js Runtime | `v24.21.0` |
| Frontend Toolchain | React `18.3.1`, TypeScript `5.8.3`, Vite `6.4.5`, Vitest `4.1.12`, Playwright `1.64.1` |
| Media Runtime | Pinned `FFmpeg 9.0.2` and `FFprobe 9.0.2` |

### A. Core Backend Representative Suite (`pytest`)

Command executed:

```powershell
.venv\Scripts\python.exe -m pytest `
  tests/test_providers_templates.py `
  tests/test_model_contracts.py `
  tests/test_provider_policy.py `
  tests/test_provider_runtime.py `
  tests/test_generation_gate.py `
  tests/test_generation_jobs.py `
  tests/test_video_generation.py `
  tests/test_video_cache.py `
  tests/test_video_recovery.py `
  tests/test_pixstag_adapter.py `
  tests/test_seedance_adapter.py `
  tests/test_editing.py `
  tests/test_delivery.py `
  tests/test_delivery_frame_boundaries.py `
  tests/test_backup_restore.py `
  tests/test_logging_rotation.py `
  tests/test_workspace_write.py -q
```

- **Result**: **`253 passed, 1 skipped, 0 failed`** in `409.09s` (`0:06:49`), exit code `0`.
- **Skipped case**: `tests/test_logging_rotation.py:57` (`symlink creation unavailable` — standard unprivileged Windows symlink guard).
- **Targeted extra check** (`tests/test_delivery_frame_boundaries.py`, `tests/test_image_default_model.py`): **`4 passed, 0 failed`** in `2.62s`, exit code `0`.

### B. Frontend Typecheck, Unit Tests & Production Build

Commands executed:

```powershell
./scripts/test-frontend.ps1
./scripts/build-ui.ps1
```

- **TypeScript (`tsc --noEmit`)**: **PASS** (`0` errors).
- **Vitest (`vitest run`)**: **`20` test files passed (`20`), `128` tests passed (`128`), `0` failed** in `22.80s`.
- **Vite Production Build (`tsc -b && vite build`)**: **PASS** — `301 modules transformed`, `dist/index.html` (`0.47 kB`), `dist/assets/index-DTFSChJm.css` (`98.53 kB`), `dist/assets/index-CFJ15RUQ.js` (`789.40 kB`), built in `1.68s`, exit code `0`.

### C. Demo Video Artifact Verification (`FFprobe` & Full Decode)

- **Output file**: `demo/kinoweave-studio-demo.mp4`
- **FFprobe metadata**: `duration = 104.20s`, `1280x720`, codec `h264`, pixel format `yuv420p`, `30/1 fps`, size `3,328,968 bytes`.
- **Full stream decode check** (`ffmpeg -v error -i demo/kinoweave-studio-demo.mp4 -f null -`): **PASS** (`0` stderr lines, exit code `0`).

### D. Bridge Runtime Integrity Check (`verify_runtime`) — Honest Fail-Closed Behavior

Command executed:

```powershell
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from kinoweave_bridge.runtime import verify_runtime; print(verify_runtime())"
```

- **Observed behavior**: Raises `kinoweave_bridge.errors.ApiError: Verified runtime is unavailable.` (`503 RUNTIME_UNAVAILABLE`).
- **Root cause (verified)**: `src/kinoweave_bridge/core_identity.json` remains pinned to the frozen closure commit `724f79b`, whereas the current working tree is at `b31e426` with active uncommitted Core/integration changes (`25` added files under `src/kinoweave/integrations/`, `13` modified Core modules, and CRLF bytes in active working files).
- **Engineering takeaway**: This demonstrates that the Bridge's fail-closed cryptographic integrity check refuses to open an HTTP socket whenever `src/kinoweave/` drifts from the signed `core_identity.json` manifest. Re-pinning `core_identity.json` on LF-normalized Core commits is explicitly tracked in **Workstream 5** (`docs/DEVIN_BOTS_ROADMAP.md`).

---

## 2. Historical Frozen Acceptance Baseline (Commit `724f79b`, `2026-11-11`)

Recorded in the source repository's `DAILY_WORKFLOW_FINAL_CLOSURE_REPORT.md` on the frozen `724f79b` commit (prior to subsequent `b31e426` integration commits; **not** re-run in full during this showcase prep):

| Scope | Historical Recorded Result | Transport / Data Boundary |
| --- | --- | --- |
| Full Backend Suite | `1,818 PASS / 3 SKIP / 0 FAIL` (`1:17:59`, exit `0`) | Offline / local TLS test endpoints; 3 Windows symlink skips |
| Frontend Suite | `128 PASS / 20 files` + `tsc` + Vite build | Offline unit & component tests |
| New-Root Chrome E2E (`playwright.daily.config.ts`) | `1 PASS` (~1.8 min) | Real Desktop Chrome + real Bridge HTTP + local TLS APIs + test-injected video download + real FFmpeg Delivery (`640x360`, 144 frames, `full_decode=true`, SHA-256 verified) |
| Cache-First Zero-Network Recovery | `3 PASS` (`test_video_cache.py`) + live root replay | Verified `provider_requests=0`, `network=DENIED` |
| Bounded Log Rotation & Redaction | `4 PASS / 1 SKIP` (`test_logging_rotation.py`) | Windows symlink skip; enforces size/retention bounds and secret scrubbing |
| Quiesced Backup & Restore Drill | `30` files backed up & restored to original path | Matching SQLite/JSON state and HTTP export SHA-256 after restore |
