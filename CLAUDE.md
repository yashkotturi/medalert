# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MedAlert: a small FastAPI + SQLite service for hospital ward bed counts, medicine stock and incident tickets, built as an "operated" DevOps/SRE showcase. Around the API sit an uptime monitor, an SLO analyzer, a Locust load test, and an MCP server that lets an AI agent (Claude Desktop) operate the service. All data is synthetic seed data; never add real patient information.

## Commands

The Makefile has shortcuts, but on Windows without `make`, run the underlying commands directly:

```bash
pip install -r requirements-dev.txt          # all dev deps (runtime deps are in requirements.txt)
uvicorn app.main:app --reload                # API on :8000, interactive docs at /docs
pytest -v                                    # full test suite
pytest tests/test_api.py::test_incident_lifecycle -v   # single test
ruff check .                                 # lint (line length 100, rules E,F,I,B,UP)
docker compose up --build                    # needs .env (copy from .env.example)
python monitoring/monitor.py                 # polls /health, appends to monitoring/health_log.csv
python monitoring/analyze.py [csv]           # SLO report + monitoring/health_report.png
locust -f loadtest/locustfile.py --host http://localhost:8000   # UI on :8089
python mcp_server/server.py                  # MCP server over stdio (normally launched by Claude Desktop)
```

Running locally without Docker, the API key defaults to `dev-key-change-me`; `.env` is only read by Docker Compose.

## Architecture

- **`app/`**: the only code shipped in the Docker image.
  - `config.py` reads `MEDALERT_*` env vars at import time. Other modules must use `config.DB_PATH` / `config.API_KEY` via attribute access (not `from app.config import ...`), because `tests/conftest.py` monkeypatches these attributes to point each test at a fresh temp DB and a test key.
  - `db.py` owns the schema (wards, medicines, incidents, audit_log), seed data, and `get_conn()`, a context manager that commits on success and rolls back on error. `init_db()` runs from the FastAPI lifespan and seeds only empty tables. Business invariants are enforced twice: as SQL `CHECK` constraints and as explicit 400 checks in the endpoints.
  - `main.py` holds all routes. Derived fields (`free_beds`, `occupancy_pct`, `near_full`, `low_stock`) are computed in `_ward()` / `_medicine()` rather than stored. Every write endpoint takes `Depends(require_api_key)`, which checks `X-API-Key` and returns the `X-Actor` header; the write must then call `audit(conn, actor, ...)` inside the same connection/transaction. A middleware logs one JSON line per request and implements chaos fault injection (`MEDALERT_CHAOS_ERROR_RATE`, read directly in `main.py`, and never applied to `/health`).
  - `schemas.py`: Pydantic models; invalid input becomes a 422.
- **`mcp_server/server.py`**: uses the `mcp` 2.x API (`mcp.server.mcpserver.MCPServer`, `ToolAnnotations`). It talks to the API over HTTP using `MEDALERT_API_URL` / `MEDALERT_API_KEY` and sends `X-Actor: mcp-agent`; it must never touch the DB directly. That is a deliberate least-privilege design, so agent writes go through the same validation, auth and audit trail. Read tools are annotated `READ_ONLY`; write tools use `WRITE` so the MCP client asks the human for approval. It also exposes a `medalert://status` resource and a `triage_incident` prompt.
- **`monitoring/`, `loadtest/`**: standalone scripts that hit the running API over HTTP. The monitor alerts after 3 consecutive failures (optionally to `ALERT_WEBHOOK_URL`).

The backend intentionally makes no LLM calls; all reasoning happens in the MCP client.

## CI notes

`.github/workflows/ci.yml` installs only `requirements.txt` plus `httpx pytest ruff`, so tests must not import dev-only packages (pandas, matplotlib, locust, mcp). `ruff check .` covers the whole repo, including `monitoring/`, `loadtest/` and `mcp_server/`. After tests, CI builds the image, smoke-tests `/health` in a container, and on push to `main` publishes to ghcr.io.

## Conventions

Per `docs/GIT_WORKFLOW.md`: branch names `feat/`, `fix/`, `docs/`, `ci/`, `test/`; Conventional Commit messages (`type: what changed`, imperative, under ~70 chars); squash-merge PRs into `main`.
