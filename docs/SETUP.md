# MedAlert setup guide (from zero)

Work through the steps in order. Each one ends with a ✅ check so you know it worked.

## 0. Install tools (one time)

| Tool | Why | Get it |
|---|---|---|
| Python 3.11+ | runs the app | python.org (Windows: tick "Add to PATH") |
| Git | version control | git-scm.com |
| VS Code | editor | code.visualstudio.com (+ Python extension) |
| Docker Desktop | containers | docker.com/products/docker-desktop |
| Claude Desktop | MCP host for the AI agent | claude.ai/download |
| GitHub account | hosting + CI | github.com |

✅ `python --version`, `git --version`, `docker --version` all print versions.

One-time Git identity:
```bash
git config --global user.name "Yashita Kotturi"
git config --global user.email "<the email on your GitHub account>"
git config --global init.defaultBranch main
```

## 1. Put the project on GitHub

1. Unzip `medalert` somewhere simple (e.g. `~/projects/medalert`).
2. On GitHub: **New repository** → name `medalert` → Public → **don't** add a README (you have one) → Create.
3. In a terminal inside the folder:
```bash
git init
git add .
git commit -m "feat: initial MedAlert service with CI, monitoring and MCP server"
git remote add origin https://github.com/yashkotturi/medalert.git
git push -u origin main
```
4. Open the repo's **Actions** tab: the CI pipeline starts automatically.

✅ Green tick on the Actions run. Your image appears under the repo's **Packages**.

> If `git push` asks for a password, GitHub needs a token instead: install the GitHub CLI and run `gh auth login`, or create a Personal Access Token.

## 2. Run locally (Python)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
✅ http://localhost:8000/health shows `{"status":"ok"...}` and http://localhost:8000/docs opens.

Running this way, the API key is the default `dev-key-change-me` (the `.env` file is only read by Docker Compose in step 3). To try a write in `/docs`: open `PATCH /medicines/{medicine_id}` → *Try it out* → set **x-api-key** to `dev-key-change-me` → body `{"change": 20}` → Execute.

Run the tests and linter:
```bash
pytest -v
ruff check .
```
✅ All tests pass.

## 3. Run in Docker

Create your env file (`cp .env.example .env`, Windows: `copy .env.example .env`), set your own `MEDALERT_API_KEY` in it, then:
```bash
docker compose up --build
```
✅ Same `/health` and `/docs` URLs work. Stop with Ctrl+C. Data persists in a Docker volume.

Useful commands: `docker ps`, `docker logs <id>`, `docker compose down`.

## 4. Monitoring + SLO report

With the API running, in a second terminal (venv active):
```bash
python monitoring/monitor.py
```
Leave it for a few minutes. Then simulate an outage: stop the API (Ctrl+C) for ~20 seconds and start it again. You'll see a 🚨 DOWN alert, then RECOVERED.

```bash
python monitoring/analyze.py
```
✅ Prints availability, p50/p95/p99 latency, error budget, and saves `monitoring/health_report.png`.

Optional: create a Discord webhook (Server Settings → Integrations → Webhooks) and run with `ALERT_WEBHOOK_URL=<url>` to get alerts on your phone.

## 5. Load test (find a bottleneck)

```bash
locust -f loadtest/locustfile.py --host http://localhost:8000
```
Open http://localhost:8089 → 50 users, spawn rate 10 → Start. Note p95 latency and failures. Push to 200+ users and see where it degrades.

Fault injection: start the API with `MEDALERT_CHAOS_ERROR_RATE=0.2` to make 20% of requests fail, and watch how the numbers change. Record findings in `docs/POSTMORTEM.md`.

## 6. Connect the AI agent (MCP)

1. Keep the API running (`uvicorn app.main:app`).
2. Find your venv's Python path:
   - macOS/Linux: `which python` (with venv active), e.g. `/Users/you/projects/medalert/.venv/bin/python`
   - Windows: `where python`, e.g. `C:\Users\you\projects\medalert\.venv\Scripts\python.exe`
3. Claude Desktop → **Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`. Add:
```json
{
  "mcpServers": {
    "medalert": {
      "command": "/ABSOLUTE/PATH/TO/medalert/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/medalert/mcp_server/server.py"],
      "env": {
        "MEDALERT_API_URL": "http://localhost:8000",
        "MEDALERT_API_KEY": "dev-key-change-me"
      }
    }
  }
}
```
   (On Windows, use double backslashes in paths: `C:\\Users\\you\\...`.) The key must match the API's key.
4. Fully quit and reopen Claude Desktop.

✅ The tools icon in the chat box lists the `medalert` tools. Ask: *"What medicines are low on stock?"*

Troubleshooting: Claude Desktop → Settings → Developer shows server status and logs. Most problems are a wrong path or the API not running.

## 7. Daily workflow

See [GIT_WORKFLOW.md](GIT_WORKFLOW.md): branch → commit → PR → CI → merge.
