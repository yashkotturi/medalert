"""API tests. CI runs these on every push; a failing test blocks the build."""


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_wards_computes_free_beds(client):
    wards = client.get("/wards").json()
    assert len(wards) == 4
    for w in wards:
        assert w["free_beds"] == w["total_beds"] - w["occupied_beds"]


def test_near_full_flag(client):
    peds = next(w for w in client.get("/wards").json() if w["name"] == "Pediatrics")
    assert peds["near_full"] is True  # 24/25 = 96%


def test_low_stock_lists_only_items_below_minimum(client):
    names = {m["name"] for m in client.get("/medicines/low-stock").json()}
    assert names == {"Insulin (Regular)", "Oxygen Cylinder"}


def test_write_requires_api_key(client):
    r = client.patch("/medicines/1", json={"change": 10})
    assert r.status_code == 401


def test_stock_cannot_go_negative(client, auth):
    r = client.patch("/medicines/1", json={"change": -999999}, headers=auth)
    assert r.status_code == 400


def test_restock_clears_low_stock(client, auth):
    insulin = next(m for m in client.get("/medicines").json()
                   if m["name"] == "Insulin (Regular)")
    r = client.patch(f"/medicines/{insulin['id']}", json={"change": 100}, headers=auth)
    assert r.status_code == 200
    assert r.json()["low_stock"] is False


def test_occupied_cannot_exceed_total(client, auth):
    r = client.patch("/wards/1", json={"occupied_beds": 1000}, headers=auth)
    assert r.status_code == 400


def test_incident_lifecycle(client, auth):
    r = client.post("/incidents", json={"title": "API latency spike",
                                        "priority": "P2"}, headers=auth)
    assert r.status_code == 201
    inc_id = r.json()["id"]
    assert r.json()["status"] == "open"

    r = client.patch(f"/incidents/{inc_id}", json={"status": "resolved"}, headers=auth)
    assert r.json()["status"] == "resolved"


def test_invalid_priority_rejected(client, auth):
    r = client.post("/incidents", json={"title": "Bad", "priority": "P9"}, headers=auth)
    assert r.status_code == 422  # Pydantic validation


def test_writes_are_audited(client, auth):
    client.patch("/medicines/1", json={"change": 5}, headers=auth)
    log = client.get("/audit", headers=auth).json()
    assert log[0]["actor"] == "pytest"
    assert log[0]["action"] == "update_stock"
