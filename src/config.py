"""Project configuration and credential loading.

Loads Alpaca API credentials from (in order of precedence):
  1. Real environment variables (APCA_API_KEY_ID / APCA_API_SECRET_KEY)
  2. A local, git-ignored ``.env`` file in the project root.

No third-party dependency (e.g. python-dotenv) is required: the ``.env``
parser here is intentionally tiny.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data_cache"
CHARTS_DIR = PROJECT_ROOT / "charts"
REPORT_DIR = PROJECT_ROOT / "report"

for _d in (DATA_DIR, CHARTS_DIR, REPORT_DIR):
    _d.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Backtest assumptions (per assignment)
# ---------------------------------------------------------------------------
INITIAL_CAPITAL = 100_000.0
TRADING_DAYS = 252
RISK_FREE_RATE = 0.0          # annual; used for Sharpe / Sortino
COMMISSION = 0.0              # per-trade fraction of notional (0 = frictionless)

# Default universe of selectable tickers
DEFAULT_TICKERS = ["AAPL", "MSFT", "SPY", "QQQ", "NVDA"]
DEFAULT_TICKER = "AAPL"
YEARS_OF_HISTORY = 6          # >= 5 years required


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a simple KEY=VALUE .env file (no overwrite)."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_alpaca_credentials() -> tuple[str, str]:
    """Return (api_key_id, api_secret_key), loading .env if needed.

    Raises a clear error if credentials are missing.
    """
    _load_dotenv(PROJECT_ROOT / ".env")
    key_id = os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("APCA_API_SECRET_KEY")
    if not key_id or not secret:
        raise RuntimeError(
            "Alpaca credentials not found. Set APCA_API_KEY_ID and "
            "APCA_API_SECRET_KEY as environment variables, or create a .env "
            "file in the project root with those two keys."
        )
    return key_id, secret
