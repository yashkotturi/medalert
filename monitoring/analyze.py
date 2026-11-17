"""Turn the monitor's CSV into reliability numbers + a chart.

Run:  python monitoring/analyze.py [path/to/health_log.csv]

Key terms:
- SLI (indicator): what you measure, e.g. % of successful health checks.
- SLO (objective): your target, e.g. 99.5% availability, p95 latency < 300 ms.
- Error budget: how much failure the SLO allows (100% - 99.5% = 0.5%).
- p95 latency: 95% of requests were faster than this. Averages hide slow outliers.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to a file, no screen needed
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

AVAILABILITY_SLO = 99.5   # percent
LATENCY_SLO_MS = 300

csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else "monitoring/health_log.csv")
df = pd.read_csv(csv_path, parse_dates=["timestamp"])
if df.empty:
    sys.exit("No data yet. Run monitor.py first.")

checks = len(df)
availability = df["up"].mean() * 100
up_latency = df.loc[df["up"] == 1, "latency_ms"]
p50 = up_latency.quantile(0.50)
p95 = up_latency.quantile(0.95)
p99 = up_latency.quantile(0.99)

allowed_failures = checks * (100 - AVAILABILITY_SLO) / 100
actual_failures = int((df["up"] == 0).sum())
budget_used = actual_failures / allowed_failures * 100 if allowed_failures else float("inf")

print(f"Checks analysed : {checks}  ({df['timestamp'].min()} -> {df['timestamp'].max()})")
print(f"Availability    : {availability:.2f}%  (SLO {AVAILABILITY_SLO}%) "
      f"{'✅' if availability >= AVAILABILITY_SLO else '❌'}")
print(f"Latency p50/p95/p99 : {p50:.1f} / {p95:.1f} / {p99:.1f} ms  "
      f"(SLO p95 < {LATENCY_SLO_MS} ms) {'✅' if p95 < LATENCY_SLO_MS else '❌'}")
print(f"Error budget used : {budget_used:.0f}%  "
      f"({actual_failures} failures, {allowed_failures:.1f} allowed)")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df["timestamp"], df["latency_ms"], linewidth=1, label="latency (ms)")
down = df[df["up"] == 0]
ax.scatter(down["timestamp"], down["latency_ms"], color="red", zorder=3, label="failed check")
ax.axhline(LATENCY_SLO_MS, linestyle="--", color="gray", label=f"SLO {LATENCY_SLO_MS} ms")
ax.set_title(f"MedAlert health: {availability:.2f}% available, p95 {p95:.0f} ms")
ax.set_ylabel("ms")
ax.legend()
fig.autofmt_xdate()
out = csv_path.with_name("health_report.png")
fig.savefig(out, dpi=120, bbox_inches="tight")
print(f"Chart saved to {out}")
