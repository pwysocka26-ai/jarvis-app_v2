# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Jarvis actually is

Day-planning assistant with three deployable surfaces against one Python backend:

1. **`frontend/` — React+Vite web app (the primary product).** Runs on `http://localhost:5173` via `npm run dev`. When the user says "aplikacja"/"apka"/"UI", they mean this. `src/App.tsx` is a single ~4.5k-line monolith; all screens (Home, Plan, Chat, Calendar, Projects, Settings) live in that one file.
2. **`jarvis-mobile/` — React Native / Expo SDK 52.** Secondary / experimental. Do **not** dual-implement features here unless explicitly asked. Has two parallel scaffolds (`App.tsx` monolith vs `app/(tabs)/` Expo Router) — `index.js` picks which runs.
3. **`app/` — FastAPI backend.** Two separate ASGI apps: `app.main` (legacy `/chat` + `/v1/*` + approvals + admin audit, see `app/main.py`) and `app.mobile_main` (mobile endpoints under `/mobile/*`, see `app/api/mobile.py` → `app/services/mobile_service.py`).

## Backend architecture (the parts you can't discover by reading one file)

Request flow: `app/api/chat.py` → `app/orchestrator/core.py::handle_chat` → `app/intent/router.py::route_intent` → domain modules in `app/b2c/` (tasks, travel_mode, maps) or `app/pro/` (filesystem tooling). Keep edits inside the right layer — API thin, orchestrator sequences, intent classifies, b2c/pro execute.

**Dual-mode persona.** `settings.persona` is `"b2c"` or `"pro"`; `pro_enabled` gates PRO filesystem tooling. `JARVIS_FS_ALLOW_WRITE` is off by default and must stay off in cloud.

**Memory has two swappable backends** selected by `MEMORY_BACKEND`: `"file"` (JSON at `MEMORY_PATH`, default `data/memory.json`) or `"db"` (SQLAlchemy, default SQLite `data/jarvis.db`). Always go through `app.memory.factory.get_memory_store(user_id)` — don't read JSON or hit SQLA directly from business logic.

**Pydantic v1/v2 compat.** `app/config.py` imports `BaseSettings` from `pydantic_settings` with a v1 fallback, and uses `default_factory=lambda: os.getenv(...)` instead of `Field(env=...)` (deprecated in v2). Follow this pattern when adding settings.

**Auth token.** `verify_token` accepts both `API_TOKEN` and `JARVIS_API_TOKEN` env vars; default dev value is `"dev-token"`. `app/api/chat.py` re-exports `_auth = verify_token` for legacy imports — don't rename.

**Alembic uses SQLite** (`./jarvis.db`) per `alembic.ini`, but runtime config (`settings.database_url`) defaults to `sqlite:///./data/jarvis.db`. They're not the same path — be explicit about which DB you're touching.

## Frontend architecture

Everything runs off `frontend/src/App.tsx`. State is lifted to the root `App` component: `activeTab`, `settingsPath`, `showNotifications`, `homeDetail`, `shoppingPool`, `events`, `projectItems`, `chatMessages`, `readIds`, `dismissedIds`. Persistence:

- Calendar/projects/chat → one blob in `localStorage` key `jarvis_calendar_v6_state`.
- Everything else uses individual `jarvis_*_v1` keys (profile, ollama URL/model, consents, permissions, notifications read/dismissed).
- Data model: `ProjectItem` has `dueAt: string | null` (ISO `YYYY-MM-DD` or null = Inbox). Backfill on read handles older stored items without this field.

**Navigation without a router.** Tabs are a union `TabId`. Sub-screens in Settings (`path: SettingsPath`) and overlays (`homeDetail`, `showNotifications`) are sibling states in `App` that short-circuit the tab switch. `NavContext` exposes `goToAccount()` / `openNotifications()` / `unreadCount` so headers can trigger global navigation without prop drilling.

**Ollama from the frontend** goes to `${readOllamaUrl()}/api/chat` with `${readOllamaModel()}` — both read from localStorage at call time, overridable in Settings. Don't reintroduce the hardcoded `http://127.0.0.1:11434`.

**Brand icons** live in `react-icons/si` (+ `react-icons/fa6` for Microsoft). Tile pattern: SVG in brand color on the same color at ~8% alpha (`${color}15`).

**Permissions screen actually calls browser APIs** (`Notification.requestPermission`, `getUserMedia`, `geolocation.getCurrentPosition`). Toggling off only clears the persisted preference — browsers don't expose a revoke API. Mic + location require secure context; on LAN IP the toggles short-circuit with an explanation.

## Commands

Activate venv first (`. .venv\Scripts\Activate.ps1` on Windows, `.venv/bin/activate` elsewhere).

```bash
# Backend — main FastAPI app (chat, approvals, admin, health)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# or:
python -m app.main

# Backend — mobile FastAPI app (/mobile/* endpoints)
python -m uvicorn app.mobile_main:app --host 127.0.0.1 --port 8011

# Tests (runs pytest with coverage against app/)
.\run_tests.cmd                          # Windows convenience wrapper
python -m pytest                         # direct
python -m pytest tests/test_foo.py::test_bar  # single test

# Alembic migrations (SQLite jarvis.db at repo root)
alembic upgrade head
alembic revision --autogenerate -m "message"

# Optional Postgres + Redis (when MEMORY_BACKEND=db)
docker compose up -d db redis

# Frontend (the main product)
cd frontend && npm install
cd frontend && npm run dev       # http://localhost:5173
cd frontend && npm run build

# CLI chat against running backend
python tools/chat_cli.py          # needs API running on API_URL
```

**Convenience scripts:** `start_jarvis.ps1` spawns server + CLI in two windows, sets `API_TOKEN`/`JARVIS_API_TOKEN`/`OLLAMA_*`. **Side effect:** it runs `git checkout work` (creates the branch if missing) before starting — don't be surprised by branch switches.

## Conventions worth knowing

- Commit style is conventional: `feat(scope): …`, `fix(scope): …` (see `git log`). Scopes in use: `chat`, `calendar`, `projects`, `settings`.
- Main branch is `main`. Don't push to `work` as if it's shared — it's a per-dev sandbox that `start_jarvis.ps1` assumes.
- Lots of `*.bak*` and `README_*.txt` / `PATCH_*.txt` in the repo root and `frontend/src/` are historical patch notes, not active code. Don't edit them. `app/api/chat.py.bak_*`, `frontend/src/App.tsx.bak*`, `app/orchestrator/core.py.bak_*` are old snapshots.
- `frontend/.vite/deps/` is Vite's dependency cache — never commit it (currently not gitignored, just leave it in `git status` noise).
