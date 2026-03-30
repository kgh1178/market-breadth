"""시장 설정 및 전역 상수"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass(frozen=True)
class MarketConfig:
    market_id: str
    name: str
    exchange_cal_code: str       # exchange_calendars 코드
    yf_suffix: str               # yfinance 종목 접미사
    constituent_source_url: str  # 1순위 소스
    constituent_fallback_url: str # 2순위 소스
    expected_count: int          # 기대 종목 수
    estimated_icc: float         # 급내상관 초기값
    ex_div_months: List[int]     # 배당락 시즌 월
    ex_div_window_days: int      # 배당락 윈도우 (영업일)
    special_metrics: List[str] = field(default_factory=list)

SP500 = MarketConfig(
    market_id="sp500",
    name="S&P 500",
    exchange_cal_code="XNYS",
    yf_suffix="",
    constituent_source_url="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    constituent_fallback_url="https://yfiua.github.io/index-constituents/constituents-sp500.json",
    expected_count=503,
    estimated_icc=0.08,
    ex_div_months=[3, 6, 9, 12],
    ex_div_window_days=1,
)

NIKKEI225 = MarketConfig(
    market_id="nikkei225",
    name="Nikkei 225",
    exchange_cal_code="XTKS",
    yf_suffix=".T",
    constituent_source_url="https://en.wikipedia.org/wiki/Nikkei_225",
    constituent_fallback_url="https://yfiua.github.io/index-constituents/constituents-nikkei225.json",
    expected_count=225,
    estimated_icc=0.10,
    ex_div_months=[3, 9],
    ex_div_window_days=2,
    special_metrics=["pwds"],
)

KOSPI200 = MarketConfig(
    market_id="kospi200",
    name="KOSPI 200",
    exchange_cal_code="XKRX",
    yf_suffix=".KS",
    constituent_source_url="pykrx://1028",  # pykrx 내부 프로토콜
    constituent_fallback_url="https://data.krx.co.kr",  # KRX OTP fallback
    expected_count=200,
    estimated_icc=0.12,
    ex_div_months=[12],
    ex_div_window_days=2,
    special_metrics=["ex_top5_spread"],
)

MARKETS = {"sp500": SP500, "nikkei225": NIKKEI225, "kospi200": KOSPI200}
MA_WINDOWS = [50, 200]
OUTPUT_DIR = Path("docs/api")
BATCH_SIZE = 30
BATCH_SLEEP = 2.0
MAX_RETRIES = 3
MIN_COVERAGE_PCT = 85.0
