"""Uptime + latency monitor (a tiny "synthetic check", like Pingdom or Datadog).

Every INTERVAL seconds it calls /health, records the result to a CSV, and
raises an alert when the service fails several checks in a row.

Run:  python monitoring/monitor.py
Env:  MEDALERT_URL (default http://127.0.0.1:8000)
      MONITOR_INTERVAL seconds (default 5)
      MONITOR_LATENCY_SLO_MS (default 300)
      ALERT_WEBHOOK_URL optional Discord/Slack webhook
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

# 127.0.0.1, not "localhost": on Windows "localhost" resolves to IPv6 ::1 first,
# uvicorn listens on IPv4 only, and the fallback adds ~2 s to every check.
URL = os.getenv("MEDALERT_URL", "http://127.0.0.1:8000").rstrip("/") + "/health"
INTERVAL = float(os.getenv("MONITOR_INTERVAL", "5"))
LATENCY_SLO_MS = float(os.getenv("MONITOR_LATENCY_SLO_MS", "300"))
FAILURES_BEFORE_ALERT = 3  # avoid alerting on a single blip (reduces alert fatigue)
WEBHOOK = os.getenv("ALERT_WEBHOOK_URL")
CSV_PATH = Path(os.getenv("MONITOR_CSV", "monitoring/health_log.csv"))


# Build the client once: creating one per request loads the SSL CA bundle each
# time (~0.5-1 s on Windows), and that cost was being counted as API latency.
# Keep-alive is off so every check still opens a fresh connection, like a real
# synthetic check would.
CLIENT = httpx.Client(timeout=2, limits=httpx.Limits(max_keepalive_connections=0))


def check() -> tuple[bool, float, int | None, str]:
    start = time.perf_counter()
    try:
        r = CLIENT.get(URL)
        ms = (time.perf_counter() - start) * 1000
        return r.status_code == 200, ms, r.status_code, ""
    except httpx.HTTPError as exc:
        ms = (time.perf_counter() - start) * 1000
        return False, ms, None, type(exc).__name__


def alert(message: str) -> None:
    print(f"🚨 ALERT: {message}")
    if WEBHOOK:
        try:
            # Discord uses "content", Slack uses "text"; sending both works for either.
            httpx.post(WEBHOOK, json={"content": message, "text": message}, timeout=3)
        except httpx.HTTPError as exc:
            print(f"   (could not send webhook: {exc})")


def main() -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_PATH.exists()
    consecutive_failures = 0
    alerted = False

    print(f"Monitoring {URL} every {INTERVAL}s (latency SLO {LATENCY_SLO_MS} ms). Ctrl+C to stop.")
    with CSV_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp", "up", "latency_ms", "status_code", "error"])
        while True:
            up, ms, code, err = check()
            writer.writerow([datetime.now().isoformat(timespec="seconds"),
                             int(up), round(ms, 2), code or "", err])
            f.flush()

            flag = "" if ms <= LATENCY_SLO_MS else "  (slow: above SLO)"
            print(f"{'UP  ' if up else 'DOWN'} {ms:7.1f} ms  {code or err}{flag}")

            if up:
                if alerted:
                    alert(f"MedAlert RECOVERED after {consecutive_failures} failed checks")
                consecutive_failures, alerted = 0, False
            else:
                consecutive_failures += 1
                if consecutive_failures >= FAILURES_BEFORE_ALERT and not alerted:
                    alert(f"MedAlert DOWN: {consecutive_failures} failed checks in a row "
                          f"(last: {code or err})")
                    alerted = True
            time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
