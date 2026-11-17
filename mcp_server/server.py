"""MedAlert MCP server: lets an AI agent (e.g. Claude Desktop) operate MedAlert.

How it works:
  Claude Desktop (host) --MCP over stdio--> this server --HTTP--> MedAlert API

- The LLM decides WHICH tool to call, based on each tool's name + docstring.
- This code does the actual work, through the API (never touching the DB
  directly), so the agent gets the same validation, auth and audit log as
  any other client. That is least privilege.
- Read tools are marked read-only. Write tools are marked as such, so the
  client asks the human for approval before running them.

Run standalone (for testing):  python mcp_server/server.py
Normally Claude Desktop starts it for you (see docs/SETUP.md).
Requires the `mcp` package, version 2.x.
"""

import os
import time

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

API_URL = os.getenv("MEDALERT_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("MEDALERT_API_KEY", "dev-key-change-me")
HEADERS = {"X-API-Key": API_KEY, "X-Actor": "mcp-agent"}

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False,
                        open_world_hint=False)

mcp = MCPServer(
    name="medalert",
    instructions=(
        "Tools for MedAlert, a hospital bed and medicine availability service. "
        "Use read tools freely. Only create incidents or change stock when the "
        "user asks or clearly agrees. Data is synthetic; never request patient details."
    ),
)


def _get(path: str):
    r = httpx.get(f"{API_URL}{path}", headers=HEADERS, timeout=5)
    r.raise_for_status()
    return r.json()


# ---------- Read tools ----------
@mcp.tool(annotations=READ_ONLY)
def check_service_health() -> dict:
    """Check whether the MedAlert API is up. Returns status and response time in ms."""
    start = time.perf_counter()
    try:
        r = httpx.get(f"{API_URL}/health", timeout=3)
        ms = round((time.perf_counter() - start) * 1000, 1)
        return {"up": r.status_code == 200, "status_code": r.status_code,
                "latency_ms": ms, "body": r.json()}
    except httpx.HTTPError as exc:
        return {"up": False, "error": type(exc).__name__, "detail": str(exc)}


@mcp.tool(annotations=READ_ONLY)
def get_bed_availability(ward_name: str | None = None) -> list[dict]:
    """List wards with total, occupied and free beds, occupancy %, and a near_full flag.
    Optionally filter by ward name (case-insensitive, partial match)."""
    wards = _get("/wards")
    if ward_name:
        wards = [w for w in wards if ward_name.lower() in w["name"].lower()]
    return wards


@mcp.tool(annotations=READ_ONLY)
def get_low_stock() -> list[dict]:
    """List medicines whose quantity is below their minimum safe level."""
    return _get("/medicines/low-stock")


@mcp.tool(annotations=READ_ONLY)
def list_incidents(status: str | None = "open") -> list[dict]:
    """List incidents. status: 'open', 'in_progress', 'resolved', or None for all."""
    return _get(f"/incidents?status={status}" if status else "/incidents")


# ---------- Write tools (client should ask for approval) ----------
@mcp.tool(annotations=WRITE)
def create_incident(title: str, priority: str, details: str = "") -> dict:
    """Create an incident ticket.
    priority: P1 (critical, patient-care impact), P2 (major), P3 (minor), P4 (low).
    details: what happened, likely cause, suggested fix."""
    r = httpx.post(f"{API_URL}/incidents", headers=HEADERS, timeout=5,
                   json={"title": title, "priority": priority, "details": details})
    if r.status_code >= 400:
        return {"error": r.status_code, "detail": r.json().get("detail")}
    return r.json()


@mcp.tool(annotations=WRITE)
def update_stock(medicine_name: str, change: int) -> dict:
    """Restock (positive change) or dispense (negative change) a medicine by name."""
    meds = _get("/medicines")
    matches = [m for m in meds if medicine_name.lower() in m["name"].lower()]
    if len(matches) != 1:
        return {"error": "Medicine name must match exactly one item",
                "matches": [m["name"] for m in matches]}
    r = httpx.patch(f"{API_URL}/medicines/{matches[0]['id']}", headers=HEADERS,
                    json={"change": change}, timeout=5)
    if r.status_code >= 400:
        return {"error": r.status_code, "detail": r.json().get("detail")}
    return r.json()


# ---------- Resource: read-only context the client can attach ----------
@mcp.resource("medalert://status", mime_type="text/plain")
def status_summary() -> str:
    """One-page system summary: health, near-full wards, low stock, open incidents."""
    health = check_service_health()
    if not health.get("up"):
        return f"MedAlert is DOWN: {health}"
    wards = [w for w in _get("/wards") if w["near_full"]]
    low = _get("/medicines/low-stock")
    open_inc = _get("/incidents?status=open")
    return "\n".join([
        f"Service: UP ({health['latency_ms']} ms)",
        "Near-full wards: " + (", ".join(f"{w['name']} ({w['occupancy_pct']}%)"
                                         for w in wards) or "none"),
        "Low stock: " + (", ".join(f"{m['name']} ({m['quantity']}/{m['min_quantity']})"
                                   for m in low) or "none"),
        f"Open incidents: {len(open_inc)}",
    ])


# ---------- Prompt: reusable triage template ----------
@mcp.prompt()
def triage_incident(symptoms: str) -> str:
    """Template for triaging an operational problem into an incident ticket."""
    return f"""You are an on-call SRE for MedAlert, a hospital availability service.
Reported symptoms: {symptoms}

Steps:
1. Call check_service_health, get_low_stock and get_bed_availability to gather facts.
2. Decide a priority: P1 = service down or a critical medicine/bed shortage affecting
   patient care; P2 = degraded; P3 = minor; P4 = cosmetic.
3. Write: title, priority, likely cause, evidence, suggested fix.
4. Show me the draft and ask before calling create_incident.
Use only facts from the tools. If unsure, say so instead of guessing."""


if __name__ == "__main__":
    mcp.run()  # stdio transport: Claude Desktop talks to us over stdin/stdout
