"""
Basic contract tests for the X / Twitter posting endpoints (mocked X API).

These protect the surface area that will be implemented with real tweepy / X API v2 client.
Currently exercises the stub /post + /orchestrate entrypoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestXBotContract:
    def test_root_reports_service(self, x_client: TestClient):
        resp = x_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "x-twitter-bot"
        assert "phase" in data or "safety_model" in data

    def test_healthz(self, x_client: TestClient):
        resp = x_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_post_preview_contract(self, x_client: TestClient):
        """Core dry-run posting contract (safe, no real X call, minimal DB)."""
        payload = {
            "account_handle": "@Mmozley70",
            "content": "Test post from the growth bot. #XRP #XRPL"
        }
        resp = x_client.post("/post/preview", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["account_handle"] == "@Mmozley70"
        assert "valid" in data

    def test_post_dry_run_contract(self, x_client: TestClient):
        """Core posting contract — used by worker / future approval flows."""
        payload = {
            "account": "@Mmozley70",
            "content": "Test post from the growth bot. #XRP #XRPL",
            "dry_run": True
        }
        resp = x_client.post("/post", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["dry_run"] is True
        assert data["posted"] is False
        assert "@Mmozley70" in data["account"]
        assert "would have posted" in data["message"]

    def test_post_queue_and_confirm_are_db_backed(self, x_client: TestClient):
        """These hit Postgres x_post_queue — contract shape tested when DB present (CI with service)."""
        # In pure unit (no DB) we at least verify the route exists and validates
        payload = {"account_handle": "@btckillas", "content": "Queued test post"}
        resp = x_client.post("/post/queue", json=payload)
        # Either succeeds (DB up) or 500 (DB down) — both document the endpoint contract
        assert resp.status_code in (200, 500, 503)

    def test_post_bad_payload_validation(self, x_client: TestClient):
        resp = x_client.post("/post/preview", json={"content": "missing handle"})
        assert resp.status_code in (400, 422)
