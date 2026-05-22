"""
Pytest configuration and shared fixtures for the Bwtz War Machine (Xtreme Ripple Protocol).

Provides:
- Module loaders for hyphenated app directories (agent-orchestrator, etc.)
- FastAPI TestClient fixtures for gateway, orchestrator, x-twitter-bot
- DB mocking helpers and sample data factories
- Common test data (today's date, sample schedules)
"""

import sys
from pathlib import Path
from datetime import date
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure root is importable
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_app_module(app_dir: str, unique_name: str | None = None):
    """Load a service's main.py despite the hyphen in the directory name.
    
    Uses a unique module name so multiple services can be loaded without 'main' namespace collision.
    """
    app_path = ROOT / "apps" / app_dir
    if not app_path.exists():
        raise RuntimeError(f"App directory not found: {app_path}")
    if str(app_path) not in sys.path:
        sys.path.insert(0, str(app_path))
    import importlib.util
    mod_name = unique_name or app_dir.replace("-", "_")
    spec = importlib.util.spec_from_file_location(mod_name, app_path / "main.py")
    module = importlib.util.module_from_spec(spec)
    # Also put it in sys.modules under unique name so patches work cleanly
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def root_path():
    return ROOT


@pytest.fixture
def today():
    """Fixed 'today' for deterministic tests."""
    return date(2026, 5, 21)  # arbitrary stable test date


# ---------- Sample data factories ----------

@pytest.fixture
def sample_static_schedule() -> Dict[str, List[str]]:
    """Representative static template output."""
    return {
        "@Mmozley70": ["GM post #XRP", "Building update #XRPL"],
        "@bwtzbearwitness": ["Morning story #ART", "Evening reflection"],
        "@btckillas": ["Killa GM", "Burn update"],
        "@getoffmylawn70": ["Space alert", "Night wrap"],
        "@textrpsms": ["Community ping", "Launch pack note"],
    }


@pytest.fixture
def sample_db_posts_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Shape returned by orchestrator.get_todays_posts_from_db()."""
    return {
        "@Mmozley70": [
            {"content": "GM post #XRP", "status": "pending", "source": "template"},
            {"content": "Building update #XRPL", "status": "posted", "source": "template"},
        ],
        "@btckillas": [
            {"content": "Killa GM", "status": "pending", "source": "template"},
        ],
    }


@pytest.fixture
def sample_db_rows() -> List[Dict[str, Any]]:
    """Rows as returned by worker.get_todays_posts() / DB cursor."""
    return [
        {"account_handle": "@Mmozley70", "content": "GM post #XRP", "status": "pending", "source": "template"},
        {"account_handle": "@Mmozley70", "content": "Building update #XRPL", "status": "posted", "source": "template"},
        {"account_handle": "@btckillas", "content": "Killa GM", "status": "pending", "source": "template"},
    ]


# ---------- App loaders & TestClients ----------

@pytest.fixture
def orchestrator_mod():
    """Loaded agent-orchestrator main module."""
    return _load_app_module("agent-orchestrator", "orchestrator_main")


@pytest.fixture
def orchestrator_client(orchestrator_mod):
    """FastAPI TestClient for the orchestrator (DB calls will be patched in tests)."""
    from fastapi.testclient import TestClient
    return TestClient(orchestrator_mod.app)


@pytest.fixture
def gateway_mod():
    return _load_app_module("gateway-api", "gateway_main")


@pytest.fixture
def gateway_client(gateway_mod):
    from fastapi.testclient import TestClient
    return TestClient(gateway_mod.app)


@pytest.fixture
def x_bot_mod():
    return _load_app_module("x-twitter-bot", "xbot_main")


@pytest.fixture
def x_client(x_bot_mod):
    from fastapi.testclient import TestClient
    return TestClient(x_bot_mod.app)


@pytest.fixture
def worker_mod():
    """Worker is a script (no FastAPI app yet)."""
    return _load_app_module("worker", "worker_main")


# ---------- Database mocking helpers ----------

@pytest.fixture
def mock_psycopg_connect(mocker):
    """
    Patch psycopg.connect globally for a test.
    Returns a tuple (mock_conn, mock_cursor) that tests can assert against.
    Usage:
        conn, cur = mock_psycopg_connect
        # configure return values, then call the function under test
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Support both `with get_db() as conn:` and `with conn.cursor() as cur:`
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    # Make the conn itself usable as context manager
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    mocker.patch("psycopg.connect", return_value=mock_conn)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_orchestrator_db(mocker, orchestrator_mod):
    """
    Patch the orchestrator's internal get_db so get_todays_posts_from_db uses our mock.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    # Patch the get_db function defined inside the orchestrator module
    mocker.patch.object(orchestrator_mod, "get_db", return_value=mock_conn)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_worker_db(mocker, worker_mod):
    """Patch worker's get_db."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    mocker.patch.object(worker_mod, "get_db", return_value=mock_conn)
    return mock_conn, mock_cursor


# ---------- HTTP mocking helpers (for gateway/worker) ----------

@pytest.fixture
def mock_httpx_get(mocker):
    """Return a MagicMock that can be used to patch httpx.Client or AsyncClient.get."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"daily_schedule": {"@Mmozley70": ["test post"]}}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    # For sync (worker uses httpx.Client)
    mocker.patch("httpx.Client", return_value=mock_client)
    # For async (gateway)
    async_mock_client = MagicMock()
    async_mock_client.get.return_value = mock_response
    async_mock_client.__aenter__.return_value = async_mock_client
    async_mock_client.__aexit__.return_value = None
    mocker.patch("httpx.AsyncClient", return_value=async_mock_client)

    return mock_response, mock_client
