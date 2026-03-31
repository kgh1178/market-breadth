"""
Market Breadth — Data Fetchers
==============================
v3.1  2026-03-31  Fix: YFINANCE_PARAMS 참조, 구성종목 수 검증

구성종목 소스:
  - S&P 500:   Wikipedia → yfiua fallback
  - Nikkei 225: Wikipedia → yfiua fallback
  - KOSPI 200:  pykrx → KRX OTP → yfiua fallback

가격 소스:
  - yfinance (auto_adjust=False) → Close = split-only adjusted
"""

import logging
import time
from io import StringIO

import pandas as pd
import requests
import urllib3
import yfinance as yf

from config import (
    BATCH_SIZE,
    BATCH_SLEEP_SEC,
    MARKETS,
    MAX_RETRIES,
    PRICE_COLUMN,
    RETRY_BACKOFF_BASE,
    YFINANCE_PARAMS,
)

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

YFIUA_BASE = "https://yfiua.github.io/index-constituents/constituents-{}.json"
WIKIPEDIA_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKIPEDIA_NIKKEI = "https://en.wikipedia.org/wiki/Nikkei_225"
WIKIPEDIA_KOSPI200 = "https://en.wikipedia.org/wiki/KOSPI_200"
NIKKEI_COMPONENTS = "https://indexes.nikkei.co.jp/en/nkave/index/component"


def _read_html_from_url(url: str, match: str | None = None) -> list[pd.DataFrame]:
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
        verify=False,
    )
    resp.raise_for_status()
    html = StringIO(resp.text)
    if match:
        return pd.read_html(html, match=match, header=0)
    return pd.read_html(html, header=0)


def fetch_sp500_wikipedia() -> list[str]:
    tables = _read_html_from_url(WIKIPEDIA_SP500)
    df = tables[0]
    tickers = df["Symbol"].tolist()
    tickers = [t.strip().replace(".", "-") for t in tickers]
    return sorted(set(tickers))


def fetch_nikkei225_official() -> list[str]:
    tables = _read_html_from_url(NIKKEI_COMPONENTS)
    tickers = []
    for tbl in tables:
        cols_lower = [str(c).lower() for c in tbl.columns]
        if "code" not in cols_lower:
            continue
        for col in tbl.columns:
            if str(col).lower() == "code":
                codes = tbl[col].dropna().astype(str).str.extract(r"(\d{4})")[0]
                tickers.extend([f"{code}.T" for code in codes.dropna()])
                break
    tickers = sorted(set(tickers))
    if len(tickers) >= 200:
        return tickers
    raise ValueError("Nikkei official components page did not yield enough codes")


def fetch_nikkei225_wikipedia() -> list[str]:
    tables = _read_html_from_url(WIKIPEDIA_NIKKEI)
    for tbl in tables:
        cols_lower = [str(c).lower() for c in tbl.columns]
        if any("ticker" in c or "code" in c or "symbol" in c for c in cols_lower):
            for col in tbl.columns:
                if any(kw in str(col).lower() for kw in ["ticker", "code", "symbol"]):
                    codes = tbl[col].dropna().astype(str).tolist()
                    tickers = []
                    for c in codes:
                        c = c.strip().split(".")[0]
                        if c.isdigit() and len(c) == 4:
                            tickers.append(f"{c}.T")
                    if len(tickers) >= 200:
                        return sorted(set(tickers))
        for col in tbl.columns:
            values = tbl[col].astype(str).str.extract(r"(\d{4})")[0].dropna()
            if len(values) >= 200:
                return sorted(set(f"{code}.T" for code in values))
    raise ValueError("Nikkei 225 구성종목 테이블을 찾을 수 없음")


def fetch_kospi200_wikipedia() -> list[str]:
    tables = _read_html_from_url(WIKIPEDIA_KOSPI200, match="Company|Symbol|GICS Sector")
    for tbl in tables:
        cols_lower = [str(c).lower() for c in tbl.columns]
        if "symbol" not in cols_lower:
            continue
        symbol_col = next(col for col in tbl.columns if str(col).lower() == "symbol")
        codes = tbl[symbol_col].dropna().astype(str).str.extract(r"(\d{6}|\d{4,6}|[0-9A-Z]{6})")[0]
        tickers = []
        for code in codes.dropna():
            if code.isdigit():
                tickers.append(f"{code.zfill(6)}.KS")
        if len(tickers) >= 180:
            return sorted(set(tickers))
    raise ValueError("KOSPI 200 Wikipedia components table not found")


def fetch_kospi200_pykrx() -> list[str]:
    try:
        from pykrx import stock as pykrx_stock

        codes = pykrx_stock.get_index_portfolio_deposit_file("1028")
        tickers = [f"{c}.KS" for c in codes]
        return sorted(set(tickers))
    except Exception as exc:
        logger.warning("pykrx KOSPI 200 조회 실패: %s", exc)
        raise


def fetch_kospi200_krx_otp() -> list[str]:
    otp_url = "http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
    otp_params = {
        "locale": "ko_KR",
        "indIdx": "028",
        "indIdx2": "028",
        "trdDd": pd.Timestamp.today().strftime("%Y%m%d"),
        "money": "1",
        "csvxls_is498": "false",
        "name": "fileDown",
        "url": "dbms/MDC/STAT/standard/MDCSTAT00601",
    }
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.krx.co.kr"}
    otp = requests.post(otp_url, data=otp_params, headers=headers, timeout=15).text
    download_url = "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"
    resp = requests.post(download_url, data={"code": otp}, headers=headers, timeout=15)
    df = pd.read_csv(StringIO(resp.text), encoding="euc-kr")
    code_col = [c for c in df.columns if "종목코드" in c or "코드" in c]
    if not code_col:
        code_col = [df.columns[0]]
    codes = df[code_col[0]].astype(str).str.strip().str.zfill(6).dropna()
    return sorted(set(f"{c}.KS" for c in codes if c and c != "000000"))


def fetch_yfiua_fallback(index_code: str) -> list[str]:
    url = YFIUA_BASE.format(index_code)
    resp = requests.get(url, timeout=15, verify=False)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        tickers = [
            d.get("symbol")
            or d.get("ticker")
            or d.get("Symbol")
            or d.get("Ticker")
            or ""
            for d in data
        ]
        return sorted(set(t for t in tickers if t))
    return []


def fetch_constituents(market_id: str) -> list[str]:
    cfg = MARKETS[market_id]
    fetchers = []

    if market_id == "sp500":
        fetchers = [
            ("Wikipedia", fetch_sp500_wikipedia),
            ("yfiua", lambda: fetch_yfiua_fallback("sp500")),
        ]
    elif market_id == "nikkei225":
        fetchers = [
            ("Nikkei official", fetch_nikkei225_official),
            ("Wikipedia", fetch_nikkei225_wikipedia),
            ("yfiua", lambda: fetch_yfiua_fallback("nikkei225")),
        ]
    elif market_id == "kospi200":
        fetchers = [
            ("Wikipedia", fetch_kospi200_wikipedia),
            ("pykrx", fetch_kospi200_pykrx),
            ("KRX OTP", fetch_kospi200_krx_otp),
        ]

    min_count = int(cfg.expected_count[0] * 0.85)

    for name, fn in fetchers:
        try:
            tickers = fn()
            if len(tickers) >= min_count:
                exp_min, exp_max = cfg.expected_count
                if not (exp_min <= len(tickers) <= exp_max):
                    logger.warning(
                        "[%s] %s: 종목 수 %s (예상 %s-%s)",
                        market_id,
                        name,
                        len(tickers),
                        exp_min,
                        exp_max,
                    )
                else:
                    logger.info("[%s] %s: %s개 종목 로드 성공", market_id, name, len(tickers))
                return tickers
            logger.warning(
                "[%s] %s: %s개 종목 (최소 %s 미달)",
                market_id,
                name,
                len(tickers),
                min_count,
            )
        except Exception as exc:
            logger.warning("[%s] %s 실패: %s", market_id, name, exc)

    raise RuntimeError(f"[{market_id}] 모든 구성종목 소스 실패")


def _coerce_download_frame(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        return df
    if len(tickers) == 1:
        ticker = tickers[0]
        df.columns = pd.MultiIndex.from_product([df.columns, [ticker]])
        return df
    return df


def fetch_prices(
    tickers: list[str],
    market_id: str,
) -> pd.DataFrame:
    """
    yfinance로 가격 데이터 다운로드.
    """
    all_data = []

    for batch_start in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    "[%s] 배치 %s/%s (%s종목) 다운로드 중... (시도 %s/%s)",
                    market_id,
                    batch_num,
                    total_batches,
                    len(batch),
                    attempt,
                    MAX_RETRIES,
                )
                df = yf.download(tickers=batch, **YFINANCE_PARAMS)
                df = _coerce_download_frame(df, batch)
                if df is not None and not df.empty:
                    all_data.append(df)
                    break
            except Exception as exc:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "[%s] 배치 %s 실패 (시도 %s): %s. %.0f초 후 재시도.",
                    market_id,
                    batch_num,
                    attempt,
                    exc,
                    wait,
                )
                time.sleep(wait)
        else:
            logger.error("[%s] 배치 %s 최종 실패", market_id, batch_num)

        if batch_start + BATCH_SIZE < len(tickers):
            time.sleep(BATCH_SLEEP_SEC)

    if not all_data:
        raise RuntimeError(f"[{market_id}] 가격 데이터 다운로드 완전 실패")

    combined = all_data[0] if len(all_data) == 1 else pd.concat(all_data, axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()]

    if isinstance(combined.columns, pd.MultiIndex):
        close_cols = combined[PRICE_COLUMN].columns if PRICE_COLUMN in combined.columns.get_level_values(0) else []
    else:
        close_cols = combined.columns

    n_downloaded = len(close_cols)
    n_expected = len(tickers)
    coverage = n_downloaded / n_expected if n_expected else 0.0

    logger.info(
        "[%s] 가격 다운로드 완료: %s/%s 종목 (%.1f%%)",
        market_id,
        n_downloaded,
        n_expected,
        coverage * 100,
    )

    downloaded_set = set(str(c) for c in close_cols)
    missing = [t for t in tickers if t not in downloaded_set]
    if missing:
        logger.warning(
            "[%s] 다운로드 누락 %s종목: %s%s",
            market_id,
            len(missing),
            missing[:10],
            "..." if len(missing) > 10 else "",
        )

    return combined


def fetch_prices_pykrx(
    tickers: list[str],
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """
    pykrx를 사용한 KOSPI 200 가격 데이터 대안.
    """
    try:
        from pykrx import stock as pykrx_stock

        frames = {}
        for ticker in tickers:
            code = ticker.replace(".KS", "")
            try:
                df = pykrx_stock.get_market_ohlcv(start_date, end_date, code)
                if df is not None and not df.empty:
                    frames[ticker] = df["종가"]
            except Exception as exc:
                logger.debug("pykrx %s 실패: %s", code, exc)

        if frames:
            result = pd.DataFrame(frames)
            logger.info("[kospi200] pykrx 가격 로드: %s종목", len(frames))
            return result
    except ImportError:
        logger.warning("pykrx 미설치")

    raise RuntimeError("pykrx 가격 다운로드 실패")
