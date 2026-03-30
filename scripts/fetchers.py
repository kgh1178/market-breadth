"""구성종목 수집 및 가격 다운로드"""
import pandas as pd
import numpy as np
import yfinance as yf
import time
import logging
from typing import List
from config import MarketConfig, BATCH_SIZE, BATCH_SLEEP, MAX_RETRIES
from utils import retry_with_backoff

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  구성종목 수집: 시장별 개별 함수
# ──────────────────────────────────────────────

def _fetch_sp500_wikipedia() -> List[str]:
    """Wikipedia에서 S&P 500 구성종목 추출"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url, header=0)
    df = tables[0]
    symbols = df["Symbol"].str.strip().dropna().tolist()
    # yfinance 호환 변환 및 빈 문자열 필터링
    symbols = [s.replace(".", "-") for s in symbols if s and isinstance(s, str)]
    log.info(f"S&P 500: {len(symbols)} symbols from Wikipedia")
    return symbols

def _fetch_nikkei225_wikipedia() -> List[str]:
    """Wikipedia에서 Nikkei 225 구성종목 추출"""
    url = "https://en.wikipedia.org/wiki/Nikkei_225"
    tables = pd.read_html(url, match="Company")
    # 첫 번째 매칭 테이블에서 종목코드 열 탐색
    df = tables[0]
    # 열 이름에 'Code', 'Ticker', 'Symbol' 등이 포함된 열 찾기
    code_col = None
    for col in df.columns:
        if any(kw in str(col).lower() for kw in
               ["code", "ticker", "symbol", "securities"]):
            code_col = col
            break
    if code_col is None:
        # 숫자 4자리가 가장 많은 열을 코드 열로 추정
        for col in df.columns:
            vals = df[col].astype(str)
            if vals.str.match(r'^\d{4}$').sum() > 100:
                code_col = col
                break
    if code_col is None:
        raise ValueError("Nikkei 225 Wikipedia 테이블에서 종목코드 열 미탐지")
    codes = df[code_col].astype(str).str.strip().dropna()
    codes = codes[codes.str.match(r'^\d{4}$')]
    symbols = [c + ".T" for c in codes if c]
    log.info(f"Nikkei 225: {len(symbols)} symbols from Wikipedia")
    return symbols

def _fetch_kospi200_pykrx() -> List[str]:
    """pykrx에서 KOSPI 200 구성종목 추출"""
    from pykrx import stock
    codes = stock.get_index_portfolio_deposit_file("1028")
    symbols = [c + ".KS" for c in codes if c]
    log.info(f"KOSPI 200: {len(symbols)} symbols from pykrx")
    return symbols

def _fetch_kospi200_krx_otp() -> List[str]:
    """KRX OTP POST 방식으로 KOSPI 200 구성종목 추출 (폴백)"""
    import requests
    otp_url = "http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd"
    otp_params = {
        "locale": "ko_KR",
        "indIdx": "028",    # KOSPI 200
        "indIdx2": "028",
        "trdDd": pd.Timestamp.today().strftime("%Y%m%d"),
        "money": "1",
        "csvxls_is498": "false",
        "name": "fileDown",
        "url": "dbms/MDC/STAT/standard/MDCSTAT00601"
    }
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://data.krx.co.kr"}
    otp = requests.post(otp_url, data=otp_params, headers=headers).text
    download_url = "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"
    resp = requests.post(download_url, data={"code": otp}, headers=headers)
    from io import StringIO
    df = pd.read_csv(StringIO(resp.text), encoding="euc-kr")
    # 종목코드 열 탐색
    code_col = [c for c in df.columns if "종목코드" in c or "코드" in c]
    if not code_col:
        code_col = [df.columns[0]]  # 첫 열이 코드일 가능성
    codes = df[code_col[0]].astype(str).str.strip().str.zfill(6).dropna()
    symbols = [c + ".KS" for c in codes if c and c != "000000"]
    log.info(f"KOSPI 200: {len(symbols)} symbols from KRX OTP")
    return symbols

def _fetch_from_yfiua(index_code: str, suffix: str) -> List[str]:
    """yfiua GitHub JSON에서 구성종목 추출 (최종 폴백)"""
    import requests
    url = f"https://yfiua.github.io/index-constituents/constituents-{index_code}.json"
    data = requests.get(url, timeout=30).json()
    symbols = [str(item.get("symbol", item.get("ticker", ""))).strip()
               for item in data if isinstance(item, dict)]
    # 빈 값 제거
    symbols = [s for s in symbols if s]
    # 접미사 확인 및 추가
    if suffix and symbols and not symbols[0].endswith(suffix):
        symbols = [s + suffix for s in symbols]
    log.info(f"{index_code}: {len(symbols)} symbols from yfiua GitHub")
    return symbols

# ──────────────────────────────────────────────
#  디스패처
# ──────────────────────────────────────────────

def fetch_constituents(cfg: MarketConfig) -> List[str]:
    """시장 설정에 따라 구성종목을 수집, 실패 시 폴백"""
    fetchers = []
    if cfg.market_id == "sp500":
        fetchers = [
            _fetch_sp500_wikipedia,
            lambda: _fetch_from_yfiua("sp500", cfg.yf_suffix),
        ]
    elif cfg.market_id == "nikkei225":
        fetchers = [
            _fetch_nikkei225_wikipedia,
            lambda: _fetch_from_yfiua("nikkei225", cfg.yf_suffix),
        ]
    elif cfg.market_id == "kospi200":
        fetchers = [
            _fetch_kospi200_pykrx,
            _fetch_kospi200_krx_otp,
        ]
    else:
        raise ValueError(f"Unknown market: {cfg.market_id}")

    last_error = None
    for fn in fetchers:
        try:
            symbols = fn()
            if len(symbols) >= cfg.expected_count * 0.85:
                return symbols
            log.warning(f"{cfg.market_id}: got {len(symbols)} symbols "
                        f"(expected ~{cfg.expected_count}), trying fallback")
        except Exception as e:
            last_error = e
            log.warning(f"{cfg.market_id}: {fn.__name__} failed: {e}")

    raise RuntimeError(
        f"{cfg.market_id}: all constituent fetchers failed. "
        f"Last error: {last_error}")

# ──────────────────────────────────────────────
#  가격 다운로드
# ──────────────────────────────────────────────

@retry_with_backoff(max_retries=MAX_RETRIES, initial_wait=5.0)
def _download_batch(symbols: List[str], period: str) -> pd.DataFrame:
    """yfinance 단일 배치 다운로드"""
    # 유효한 심볼만 필터링
    valid_symbols = [s for s in symbols if s and isinstance(s, str)]
    if not valid_symbols:
        return pd.DataFrame()
    df = yf.download(
        tickers=valid_symbols,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        # 'Close'가 없을 경우 'Adj Close' 시도
        if "Close" in df.columns.levels[0]:
            return df["Close"]
        elif "Adj Close" in df.columns.levels[0]:
            return df["Adj Close"]
        return pd.DataFrame()
    return df

def fetch_prices(symbols: List[str], cfg: MarketConfig,
                 lookback_days: int = 504) -> pd.DataFrame:
    """
    전체 구성종목의 종가 다운로드.
    배치 크기 BATCH_SIZE, 배치 간 BATCH_SLEEP초 대기.
    """
    # lookback_days를 yfinance period 문자열로 변환
    period = f"{lookback_days + 50}d"  # 여유분 50일
    all_dfs = []
    failed_symbols = []

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        try:
            df = _download_batch(batch, period)
            all_dfs.append(df)
        except Exception as e:
            log.error(f"{cfg.market_id}: batch {i//BATCH_SIZE} failed: {e}")
            failed_symbols.extend(batch)

        if i + BATCH_SIZE < len(symbols):
            time.sleep(BATCH_SLEEP)

    if not all_dfs:
        raise RuntimeError(f"{cfg.market_id}: no price data downloaded")

    prices = pd.concat(all_dfs, axis=1)

    # 중복 열 제거 (동일 종목이 여러 배치에 포함된 경우)
    prices = prices.loc[:, ~prices.columns.duplicated()]

    coverage = len(prices.columns) / len(symbols) * 100
    log.info(f"{cfg.market_id}: {len(prices.columns)}/{len(symbols)} "
             f"symbols downloaded ({coverage:.1f}%)")

    return prices, failed_symbols, coverage
