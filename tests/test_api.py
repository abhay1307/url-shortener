"""
Basic API tests — run with: pytest tests/
Requires a running PostgreSQL instance (set DATABASE_URL env var).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@patch("app.services.cache.get_cached_url", return_value=None)
@patch("app.services.cache.cache_url", return_value=None)
@patch("app.services.publisher.publish_click", return_value=None)
def test_shorten_and_redirect(mock_pub, mock_cache_write, mock_cache_read):
    # Shorten
    res = client.post("/api/shorten", json={"url": "https://github.com"})
    assert res.status_code == 200
    data = res.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert "short_url" in data

    # Redirect (follow=False so we catch the 302)
    code = data["short_code"]
    res2 = client.get(f"/{code}", follow_redirects=False)
    assert res2.status_code in (302, 307)
    assert "github.com" in res2.headers["location"]


def test_shorten_invalid_url():
    res = client.post("/api/shorten", json={"url": "not-a-url"})
    assert res.status_code == 422


def test_redirect_not_found():
    res = client.get("/xxxxxx", follow_redirects=False)
    assert res.status_code == 404


def test_analytics_not_found():
    res = client.get("/api/analytics/xxxxxx")
    assert res.status_code == 404


def test_analytics_list():
    res = client.get("/api/analytics")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
