# Postmortem: [title, e.g. "Write latency spike under load"]

> Blameless format: focus on the system and process, not on people.
> Fill this in after your load test or chaos test. This is your strongest interview story.

**Date:** YYYY-MM-DD  **Severity:** P2  **Status:** Resolved  **Author:** Yashita Kotturi

## Summary
Two or three sentences: what happened, impact, how it was fixed.

## Impact
- Who/what was affected (e.g. stock updates slowed for staff)
- Duration
- SLO impact: availability X%, p95 latency Y ms (SLO: < 300 ms), error budget used Z%

## Timeline
| Time | Event |
|---|---|
| 00:00 | Load test started, 50 users |
| 00:02 | p95 latency rose above SLO |
| 00:03 | Monitor alerted / noticed in Locust |
| 00:10 | Root cause identified |
| 00:20 | Fix deployed, latency back within SLO |

## Root cause
What actually caused it, with evidence (logs, Locust numbers, chart).
Example to investigate: SQLite allows only one writer at a time, so concurrent
`PATCH /medicines` requests wait for the lock.

## Resolution
What you changed (e.g. enabled WAL mode / added a busy timeout / reduced
transaction scope) and the **before → after** numbers.

## What went well / what didn't
- ✅ Monitor detected the issue within N seconds
- ❌ No alert on latency, only on downtime

## Action items
| Action | Type | Status |
|---|---|---|
| Add a latency alert, not just up/down | Detect | Todo |
| Move to PostgreSQL for concurrent writes | Prevent | Future |
