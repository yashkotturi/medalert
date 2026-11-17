import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

API_KEY = "test-key"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh temporary database for every test, so tests never affect each other."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "API_KEY", API_KEY)
    with TestClient(app) as c:  # "with" runs startup, which creates + seeds the DB
        yield c


@pytest.fixture
def auth():
    return {"X-API-Key": API_KEY, "X-Actor": "pytest"}
