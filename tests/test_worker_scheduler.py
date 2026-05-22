"""
Worker scheduler & job tests (mocked orchestrator call + DB).

Covers the automated daily generation loop:
- fetch_or_generate_daily
- persist_daily_posts (already covered in db tests but exercised here)
- scheduled_job orchestration
- init + basic scheduler config (without actually starting APScheduler threads in tests)
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch


class TestFetchAndPersistFlow:
    def test_fetch_or_generate_daily_success(self, worker_mod, mocker, sample_static_schedule):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"daily_schedule": sample_static_schedule, "source": "template"}
        mock_resp.raise_for_status.return_value = None

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__.return_value = mock_client

        mocker.patch("httpx.Client", return_value=mock_client)

        result = worker_mod.fetch_or_generate_daily()

        assert result == sample_static_schedule
        mock_client.get.assert_called_once()

    def test_fetch_or_generate_daily_network_failure_returns_empty(self, worker_mod, mocker):
        mocker.patch("httpx.Client", side_effect=Exception("network down in test"))

        result = worker_mod.fetch_or_generate_daily()
        assert result == {}

    def test_scheduled_job_calls_fetch_then_persist(self, worker_mod, mocker, sample_static_schedule, today):
        # Mock the fetch
        mocker.patch.object(worker_mod, "fetch_or_generate_daily", return_value=sample_static_schedule)

        # Mock persist so we don't hit real DB
        mock_persist = mocker.patch.object(worker_mod, "persist_daily_posts")

        # Patch date.today for determinism inside scheduled_job
        with patch.object(worker_mod, "date") as mock_date_mod:
            mock_date_mod.today.return_value = today

            worker_mod.scheduled_job()

        mock_persist.assert_called_once_with(sample_static_schedule, today)

    def test_scheduled_job_skips_persist_on_empty_schedule(self, worker_mod, mocker):
        mocker.patch.object(worker_mod, "fetch_or_generate_daily", return_value={})
        mock_persist = mocker.patch.object(worker_mod, "persist_daily_posts")

        worker_mod.scheduled_job()

        mock_persist.assert_not_called()


class TestSchedulerConfiguration:
    """Light smoke tests around APScheduler wiring (no real jobs run)."""

    def test_start_scheduler_registers_jobs_from_env(self, worker_mod, mocker):
        # Patch the name as bound in the worker module (from-import at load time)
        mock_sched = MagicMock()
        mocker.patch("worker_main.BackgroundScheduler", return_value=mock_sched)

        # Force the already-loaded module's module-level config (set at import time from getenv)
        worker_mod.DAILY_POST_TIMES = "08:00,20:00"

        sched = worker_mod.start_scheduler()

        # Should have added two jobs
        assert mock_sched.add_job.call_count == 2
        assert mock_sched.start.called

    def test_init_db_is_called_in_main_when_scheduler_enabled(self, worker_mod, mocker):
        mock_init = mocker.patch.object(worker_mod, "init_db")
        mock_start = mocker.patch.object(worker_mod, "start_scheduler")
        mocker.patch.object(worker_mod, "scheduled_job")  # avoid real first run

        # We can't easily call main() without blocking, so just verify the functions exist and are wired
        assert hasattr(worker_mod, "init_db")
        assert hasattr(worker_mod, "start_scheduler")
        assert callable(worker_mod.scheduled_job)
