# MedAlert 🏥

![CI](https://github.com/yashkotturi/medalert/actions/workflows/ci.yml/badge.svg)

**Real-time hospital bed and medicine availability, operated by an AI agent.**

Hospital staff lose critical time when they can't see which wards have free beds or which medicines are running low, and when that system goes down, patient care suffers. MedAlert is a small service built to be *operated*, not just built: it's tested and containerised through CI/CD, monitored against SLOs, and exposes an **MCP server** so an AI agent can check health, query availability and raise incident tickets, with human approval on every write.

> All data is synthetic. No patient information is stored or sent to any AI model.

## Architecture

```
 Staff / on-call engineer
          │  natural language
          ▼
  Claude Desktop (MCP host) ──MCP/stdio──▶ mcp_server/server.py
                                                  │ HTTP + API key
                                                  ▼
 GitHub ──push──▶ GitHub Actions ──▶ Docker image ──▶ FastAPI app (app/) ──▶ SQLite
  (lint → test → build → smoke test → publish)          ▲
                                                        │ /health every N s
                                         monitoring/monitor.py ──▶ CSV ──▶ analyze.py
                                                                   └──▶ alerts (webhook)
```

## Features

| Area | What it does |
|---|---|
| **API** | Ward bed counts, medicine stock, low-stock and near-full flags, incident tickets (`/docs` for interactive API docs) |
| **Security** | API key on all writes, input validation, audit log of every change, container runs as non-root |
| **CI/CD** | GitHub Actions: lint → tests → Docker build → container smoke test → publish to ghcr.io |
| **Reliability** | `/health` check, uptime/latency monitor with alerting, SLO report (availability, p95), load test, fault injection |
| **AI ops agent** | MCP server with read tools, approval-gated write tools, a status resource and a triage prompt |

## Quick start

```bash
git clone https://github.com/yashkotturi/medalert.git && cd medalert
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs. Full setup (Docker, MCP, monitoring): **[docs/SETUP.md](docs/SETUP.md)**

## Reliability results

| Metric | SLO | Measured |
|---|---|---|
| Availability | ≥ 99.5% | _fill in from `analyze.py`_ |
| p95 latency (health) | < 300 ms | _fill in_ |
| p95 latency under load (50 users) | < 300 ms | _fill in from Locust_ |

See [docs/POSTMORTEM.md](docs/POSTMORTEM.md) for the incident write-up.

## AI agent demo

Ask Claude Desktop:
- *"Which wards are nearly full and what medicines are low?"*
- *"Is MedAlert healthy? If not, draft a P1 incident."* (Claude asks before creating it)
- Use the **triage_incident** prompt with symptoms like *"API returning 500s"*

## Design decisions & trade-offs

- **SQLite**: zero setup, but a single writer at a time. Fine for one instance; **PostgreSQL** is needed for multiple replicas or heavy write load.
- **Agent goes through the API, not the database**: same validation, auth and audit trail as any client (least privilege).
- **Alert after 3 consecutive failures**: avoids alert fatigue from one-off blips, at the cost of ~3 × interval detection delay.
- **No LLM calls in the backend**: the reasoning happens in the MCP client; the backend stays deterministic, cheap and testable.

## What I'd add next

Kubernetes deployment with readiness/liveness probes and replicas · PostgreSQL · Prometheus + Grafana · SSO/MFA · Terraform for cloud infrastructure · integration with an ITSM tool such as ServiceNow

## Project structure

```
app/            FastAPI service (main.py, db.py, schemas.py, config.py)
tests/          pytest suite (runs in CI)
monitoring/     uptime monitor + SLO analysis
loadtest/       Locust load test
mcp_server/     MCP server for the AI ops agent
docs/           setup, Git workflow, postmortem
.github/        CI pipeline, PR + issue templates
```
