"""App settings, read from environment variables.

Why env vars? The same Docker image runs locally, in CI and in production.
Only the configuration changes, never the code (12-factor app principle).
Secrets like the API key must never be hard-coded or committed to Git.
"""

import os

DB_PATH = os.getenv("MEDALERT_DB_PATH", "medalert.db")
API_KEY = os.getenv("MEDALERT_API_KEY", "dev-key-change-me")
# Wards at or above this occupancy % are flagged as "near full".
NEAR_FULL_THRESHOLD = float(os.getenv("MEDALERT_NEAR_FULL_PCT", "85"))
