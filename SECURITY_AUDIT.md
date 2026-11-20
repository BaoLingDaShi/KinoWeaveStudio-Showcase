# Security & Desensitization Audit (`KinoWeaveStudio-Showcase`)

**Audit Date**: `2026-11-20`  
**Target Directory**: `D:\KinoWeaveStudio-Showcase`  
**Audit Outcome**: **PASS (0 sensitive hits, 0 paid API calls, 0 source-repo mutations)**

---

## 1. Automated Text & Pattern Scan

All `14` text files in `D:\KinoWeaveStudio-Showcase` (including `README.md`, `docs/`, `evidence/`, `demo/`, `snippets/`, `NOTICE.md`, `.gitignore`, and `SECURITY_AUDIT.md`) were scanned against automated regex checks for:

| Check Category | Patterns Verified Absent | Result |
| --- | --- | --- |
| **API Keys & Tokens** | `sk-*`, `Bearer <token>`, `BEGIN ... PRIVATE KEY`, `HUOSHEN_API_KEY=`, `PIXSTAG_API_KEY=`, `ARK_API_KEY=`, `OPENAI_API_KEY=` assignments | **0 hits** |
| **Personal User Identifiers & Local Machine Paths** | Local Windows user directory prefixes, personal user IDs, archive directory references, personal email addresses | **0 hits** |
| **Private Creative Productions & Internal Endpoints** | Non-public production slugs, private story/film scripts, non-public vendor hostnames | **0 hits** |
| **Unapproved Source Dumps** | Confirmed only `4` curated, read-only Core excerpts exist under `snippets/`; no SQLite databases, `.env` files, or deployment grants included | **PASS** |

---

## 2. Visual & Media Inspection

- **Untouched Original Screenshots (`assets/screenshots/01` – `10`)**:
  - `01`–`04` captured live from React Studio UI (`DEMO / MOCK` mode) running in isolated loopback Desktop Chrome (`127.0.0.1:5174`) with external network requests blocked.
  - `05`–`10` preserved directly from verified offline / local-TLS `LOCAL CORE` Chrome acceptance runs (`09-core-timeline-multitrack.png` cropped at `y = 1694` to remove an appended test-harness `<video>` element outside the application footer).
- **Lossless Zoomed Highlight Crops (`assets/screenshots/highlights/h1` – `h4b`)**:
  - Pure pixel crops of `10`, `09`, `05`, `06`, and `07` removing empty sidebars/footer margins for legible full-width README presentation; zero edits to underlying UI content.
  - All original and cropped screenshots visually inspected: zero pairing secrets, zero credentials, zero private paths, zero private creative manuscripts.
- **Demo Video (`demo/kinoweave-studio-demo.mp4`)**:
  - Duration: `104.20s`, `1280x720`, H.264 `yuv420p`, `30 fps`, `3,328,968` bytes.
  - Verified with `ffprobe` and full `ffmpeg -v error ... -f null -` decode (`0` errors).
  - Six extracted frames (`2s`, `22s`, `48s`, `60s`, `82s`, `96s`) visually inspected for text legibility, accurate `DEMO / MOCK` vs. `LOCAL CORE` labeling, and zero sensitive data.

---

## 3. Source Repository & Runtime Integrity Checks

- **No Paid Provider Calls**: `0` external AI provider calls were executed during screenshot capture, demo rendering, or verification runs.
- **No Production Data Touched**: `D:\KinoWeaveStudio` working tree remained completely unaltered (`git status` identical before and after showcase assembly).
- **No Leftover Services**: Loopback ports `5174` and `5184` verified closed after Chrome capture completed.
