"""
Market Breadth Indicator System — Configuration
================================================
v3.1  2026-03-31  Fix: auto_adjust=False (Barchart S5FI compatible)

가격 기준: split-adjusted, dividend-unadjusted
근거: Barchart "Calculations are adjusted for stock splits
      but not dividend distributions"
"""

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 가격 데이터 설정
# ─────────────────────────────────────────────
YFINANCE_PARAMS = {
    "period": "2y",
    "auto_adjust": False,
    "progress": False,
    "repair": True,
    "keepna": False,
}

PRICE_COLUMN = "Close"

# ─────────────────────────────────────────────
# 다운로드 제어
# ─────────────────────────────────────────────
BATCH_SIZE = 30
BATCH_SLEEP_SEC = 2.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0

# ─────────────────────────────────────────────
# 품질 기준
# ─────────────────────────────────────────────
MIN_COVERAGE_RATIO = 0.85
MAX_DAILY_RETURN = 0.40
MISSING_BLOCK_DAYS = 5

# ─────────────────────────────────────────────
# 검증 기준
# ─────────────────────────────────────────────
VALIDATION_TOLERANCE_PP = 3.0
MIN_CORRELATION = 0.97
MAX_RMSE_PP = 3.0

# ─────────────────────────────────────────────
# 마켓 정의
# ─────────────────────────────────────────────
@dataclass
class MarketConfig:
    name: str
    index_code: str
    exchange_cal: str
    ticker_suffix: str
    expected_count: tuple
    icc_estimate: float
    ex_div_buffer_days: int
    breadth_windows: tuple = (50, 200)
    special_metrics: list = field(default_factory=list)
    price_source: str = "yfinance"

    pykrx_index_code: Optional[str] = None
    pykrx_use_adjusted: bool = False


MARKETS = {
    "sp500": MarketConfig(
        name="S&P 500",
        index_code="sp500",
        exchange_cal="XNYS",
        ticker_suffix="",
        expected_count=(500, 506),
        icc_estimate=0.08,
        ex_div_buffer_days=1,
        special_metrics=["ex_top5_concentration"],
    ),
    "nikkei225": MarketConfig(
        name="Nikkei 225",
        index_code="nikkei225",
        exchange_cal="XTKS",
        ticker_suffix=".T",
        expected_count=(224, 226),
        icc_estimate=0.10,
        ex_div_buffer_days=2,
        special_metrics=["pwds"],
    ),
    "kospi200": MarketConfig(
        name="KOSPI 200",
        index_code="kospi200",
        exchange_cal="XKRX",
        ticker_suffix=".KS",
        expected_count=(199, 201),
        icc_estimate=0.12,
        ex_div_buffer_days=2,
        special_metrics=["ex_top5_spread"],
        price_source="yfinance",
        pykrx_index_code="1028",
        pykrx_use_adjusted=False,
    ),
}

# ─────────────────────────────────────────────
# 출력 경로
# ─────────────────────────────────────────────
OUTPUT_DIR = "docs/api"
GITHUB_PAGES_BASE = "https://{username}.github.io/market-breadth/api"
