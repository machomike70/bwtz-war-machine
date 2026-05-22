"""
Unit tests for DB helpers.

Covers critical persistence & retrieval paths used by the daily flow:
- worker.init_db, worker.persist_daily_posts, worker.get_todays_posts
- orchestrator.get_todays_posts_from_db (with graceful fallback)

All tests use mocks — no live Postgres required.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

# These tests import via the fixtures which handle path insertion


class TestWorkerDBHelpers:
    """Tests for apps/worker/main.py DB functions."""

    def test_init_db_creates_tables_and_seeds_accounts(self, worker_mod, mock_worker_db, mocker):
        conn, cur = mock_worker_db

        # Call
        worker_mod.init_db()

        # Assert table creation + seeding
        assert cur.execute.call_count >= 4  # accounts + daily_posts + 5 seeds (with ON CONFLICT)
        # Check important SQL fragments were executed
        sql_calls = [str(call.args[0]) if call.args else "" for call in cur.execute.call_args_list]
        assert any("CREATE TABLE IF NOT EXISTS accounts" in s for s in sql_calls)
        assert any("CREATE TABLE IF NOT EXISTS daily_posts" in s for s in sql_calls)
        assert any("INSERT INTO accounts" in s for s in sql_calls)

    def test_persist_daily_posts_inserts_and_respects_conflict(self, worker_mod, mock_worker_db, today, sample_static_schedule):
        conn, cur = mock_worker_db
        # Simulate inserts succeed
        cur.rowcount = 1
        cur.execute.return_value = None

        inserted = 0
        # We directly exercise the function
        worker_mod.persist_daily_posts(sample_static_schedule, today)

        # Should have attempted INSERT for every post
        total_posts = sum(len(v) for v in sample_static_schedule.values())
        assert cur.execute.call_count == total_posts

        # Verify one of the calls
        first_call = cur.execute.call_args_list[0]
        sql = first_call.args[0]
        params = first_call.args[1]
        assert "INSERT INTO daily_posts" in sql
        assert "ON CONFLICT" in sql
        assert params[0] in sample_static_schedule  # handle
        assert params[2] == today

    def test_get_todays_posts_returns_rows(self, worker_mod, mock_worker_db, sample_db_rows, today):
        conn, cur = mock_worker_db
        cur.fetchall.return_value = sample_db_rows

        rows = worker_mod.get_todays_posts()

        cur.execute.assert_called_once()
        sql = cur.execute.call_args.args[0]
        assert "SELECT account_handle, content, status, source" in sql
        assert "WHERE scheduled_for = %s" in sql
        assert rows == sample_db_rows

    def test_persist_handles_empty_schedule(self, worker_mod, mock_worker_db, today):
        conn, cur = mock_worker_db
        worker_mod.persist_daily_posts({}, today)
        assert cur.execute.call_count == 0


class TestOrchestratorDBHelpers:
    """Tests for apps/agent-orchestrator/main.py DB retrieval."""

    def test_get_todays_posts_from_db_groups_by_account(self, orchestrator_mod, mock_orchestrator_db, sample_db_rows, today):
        conn, cur = mock_orchestrator_db
        cur.fetchall.return_value = sample_db_rows

        # Patch date.today inside the module under test for determinism
        with patch.object(orchestrator_mod, "date") as mock_date:
            mock_date.today.return_value = today
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw) if a else today

            grouped = orchestrator_mod.get_todays_posts_from_db()

        assert "@Mmozley70" in grouped
        assert len(grouped["@Mmozley70"]) == 2
        assert grouped["@Mmozley70"][0]["status"] == "pending"
        assert "content" in grouped["@Mmozley70"][0]

    def test_get_todays_posts_from_db_returns_empty_on_no_rows(self, orchestrator_mod, mock_orchestrator_db, today):
        conn, cur = mock_orchestrator_db
        cur.fetchall.return_value = []

        with patch.object(orchestrator_mod, "date") as mock_date:
            mock_date.today.return_value = today
            result = orchestrator_mod.get_todays_posts_from_db()

        assert result == {}

    def test_get_todays_posts_from_db_graceful_fallback_on_exception(self, orchestrator_mod, mock_orchestrator_db, today):
        conn, cur = mock_orchestrator_db
        cur.execute.side_effect = Exception("DB is down for test")

        with patch.object(orchestrator_mod, "date") as mock_date:
            mock_date.today.return_value = today
            result = orchestrator_mod.get_todays_posts_from_db()

        # Critical: never crash the dashboard — fallback to {}
        assert result == {}

    def test_get_db_returns_connection(self, orchestrator_mod, mocker):
        mock_conn = MagicMock()
        mocker.patch("psycopg.connect", return_value=mock_conn)
        # The orchestrator get_db is a thin wrapper
        conn = orchestrator_mod.get_db()
        assert conn is mock_conn
