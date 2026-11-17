"""Load test: simulate many hospital staff using MedAlert at once.

Run (with the API running):
    locust -f loadtest/locustfile.py --host http://localhost:8000
Then open http://localhost:8089, try 50 users with spawn rate 10.

Headless example (60 s, saves CSV results):
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 50 -r 10 -t 60s --csv loadtest/results

What to look for: p95 latency, failure %, and how they change as users grow.
The write tasks stress SQLite's single-writer lock: a real bottleneck to find,
measure, explain and fix.
"""

import os
import random

from locust import HttpUser, between, task

HEADERS = {"X-API-Key": os.getenv("MEDALERT_API_KEY", "dev-key-change-me"),
           "X-Actor": "loadtest"}


class HospitalStaff(HttpUser):
    wait_time = between(0.5, 2)

    @task(5)  # reads are the most common action
    def view_wards(self):
        self.client.get("/wards")

    @task(3)
    def view_low_stock(self):
        self.client.get("/medicines/low-stock")

    @task(1)
    def dispense_and_restock(self):
        med_id = random.randint(1, 5)
        self.client.patch(f"/medicines/{med_id}", json={"change": 1},
                          headers=HEADERS, name="/medicines/[id]")
