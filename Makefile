# Shortcuts. On Windows without `make`, run the commands on the right directly.
.PHONY: install run test lint docker monitor report load mcp

install:   ## create venv deps
	pip install -r requirements-dev.txt

run:       ## run API with auto-reload
	uvicorn app.main:app --reload

test:
	pytest -v

lint:
	ruff check .

docker:    ## build + run in Docker
	docker compose up --build

monitor:   ## start uptime/latency monitor
	python monitoring/monitor.py

report:    ## analyse monitor CSV
	python monitoring/analyze.py

load:      ## open Locust UI on :8089
	locust -f loadtest/locustfile.py --host http://localhost:8000

mcp:       ## run MCP server standalone (normally Claude Desktop starts it)
	python mcp_server/server.py
