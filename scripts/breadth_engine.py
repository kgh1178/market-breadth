"""
Market Breadth Engine
=====================
v3.1  2026-03-31  Fix: split-only adjusted price, n_valid denominator

핵심 원칙:
  - Close 열만 사용 (split-adjusted, dividend-unadjusted)
  - Adj Close 열은 절대 참조하지 않음
  - SMA(W)는 min_periods=W 로 데이터 부족 종목 자동 NaN 처리
  - 분모는 n_valid (SMA 산출 가능 종목 수)
"""

import logging

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from config import PRICE_COLUMN

logger = logging.getLogger(__name__)


def _extract_close(prices_df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(prices_df.columns, pd.MultiIndex):
        return prices_df[PRICE_COLUMN].copy()
    if PRICE_COLUMN in prices_df.columns:
        return prices_df[[PRICE_COLUMN]].copy()
    return prices_df.copy()


def compute_breadth(
    prices_df: pd.DataFrame,
    window: int = 50,
) -> dict:
    """
    Barchart S5FI 호환 breadth 계산.
    """
    close = _extract_close(prices_df)
    sma = close.rolling(window=window, min_periods=window).mean()

    latest_close = close.iloc[-1]
    latest_sma = sma.iloc[-1]

    valid_mask = latest_close.notna() & latest_sma.notna()
    n_valid = int(valid_mask.sum())
    n_total = len(latest_close)

    above_mask = (latest_close > latest_sma) & valid_mask
    n_above = int(above_mask.sum())

    breadth = (n_above / n_valid * 100) if n_valid > 0 else np.nan

    per_stock = {}
    for ticker in latest_close.index:
        if bool(valid_mask.get(ticker, False)):
            per_stock[ticker] = {
                "close": round(float(latest_close[ticker]), 4),
                "sma": round(float(latest_sma[ticker]), 4),
                "above": bool(above_mask[ticker]),
            }

    result = {
        "breadth": round(breadth, 2) if not np.isnan(breadth) else None,
        "n_above": n_above,
        "n_valid": n_valid,
        "n_total": n_total,
        "n_excluded": n_total - n_valid,
        "window": window,
        "per_stock": per_stock,
    }

    logger.info(
        "Breadth(W=%s): %s%% (%s/%s, excluded=%s)",
        window,
        result["breadth"],
        n_above,
        n_valid,
        result["n_excluded"],
    )
    return result


def compute_breadth_timeseries(
    prices_df: pd.DataFrame,
    window: int = 50,
    lookback: int = 504,
) -> pd.DataFrame:
    """
    과거 lookback 거래일에 대한 일별 breadth 시계열.
    """
    close = _extract_close(prices_df)
    sma = close.rolling(window=window, min_periods=window).mean()

    records = []
    start_idx = max(0, len(close) - lookback)

    for i in range(start_idx, len(close)):
        row_close = close.iloc[i]
        row_sma = sma.iloc[i]
        valid = row_close.notna() & row_sma.notna()
        n_valid = int(valid.sum())
        n_above = int(((row_close > row_sma) & valid).sum())
        breadth = (n_above / n_valid * 100) if n_valid > 0 else np.nan

        records.append({
            "date": close.index[i].strftime("%Y-%m-%d"),
            "breadth": round(breadth, 2) if not np.isnan(breadth) else None,
            "n_above": n_above,
            "n_valid": n_valid,
        })

    return pd.DataFrame(records)


def compute_deff_ci(
    n_above: int,
    n_valid: int,
    icc: float = 0.08,
    alpha: float = 0.05,
) -> dict:
    """
    Design Effect (DEFF) 보정된 Clopper-Pearson 신뢰구간.
    """
    if n_valid == 0:
        return {"lower": None, "upper": None, "deff": None, "n_eff": None}

    deff = 1.0 + (n_valid - 1) * icc
    n_eff = n_valid / deff
    p_hat = n_above / n_valid

    k_eff = round(p_hat * n_eff)
    n_eff_int = round(n_eff)

    if n_eff_int <= 0:
        return {
            "lower": None,
            "upper": None,
            "deff": round(deff, 2),
            "n_eff": round(n_eff, 1),
        }

    lower = sp_stats.beta.ppf(alpha / 2, k_eff, n_eff_int - k_eff + 1) * 100
    upper = sp_stats.beta.ppf(1 - alpha / 2, k_eff + 1, n_eff_int - k_eff) * 100

    return {
        "lower": round(float(lower), 2),
        "upper": round(float(upper), 2),
        "deff": round(deff, 2),
        "n_eff": round(n_eff, 1),
    }


def compute_pwds(
    prices_df: pd.DataFrame,
    weights: pd.Series | None = None,
    window: int = 50,
) -> float:
    """
    Price-Weighted Divergence Score (PWDS) for Nikkei 225.
    """
    close = _extract_close(prices_df)
    sma = close.rolling(window=window, min_periods=window).mean()
    latest_close = close.iloc[-1]
    latest_sma = sma.iloc[-1]

    valid = latest_close.notna() & latest_sma.notna()
    above = (latest_close > latest_sma) & valid

    if weights is None:
        weights = latest_close[valid]

    common_tickers = list(set(weights.index) & set(above.index))
    if not common_tickers:
        return np.nan

    w = weights[common_tickers]
    w_norm = w / w.sum()
    weighted_breadth = (above[common_tickers].astype(float) * w_norm).sum() * 100
    equal_breadth = above[common_tickers].mean() * 100

    pwds = weighted_breadth - equal_breadth
    return round(float(pwds), 2)


def compute_ex_top5_spread(
    prices_df: pd.DataFrame,
    market_cap: pd.Series | None = None,
    window: int = 50,
) -> float:
    """
    Cap-Weighted Breadth Spread (CWBS) for KOSPI 200.
    """
    close = _extract_close(prices_df)
    sma = close.rolling(window=window, min_periods=window).mean()
    latest_close = close.iloc[-1]
    latest_sma = sma.iloc[-1]

    valid = latest_close.notna() & latest_sma.notna()
    above = (latest_close > latest_sma) & valid

    n_valid = int(valid.sum())
    total_breadth = above.sum() / n_valid * 100 if n_valid > 0 else np.nan

    if market_cap is None:
        market_cap = close.tail(20).mean()

    common = list(set(market_cap.index) & set(valid[valid].index))
    if len(common) < 6:
        return np.nan

    top5 = market_cap[common].nlargest(5).index
    ex_top5_valid = valid.drop(top5, errors="ignore")
    ex_top5_above = above.drop(top5, errors="ignore")
    n_ex = int(ex_top5_valid.sum())
    ex_breadth = ex_top5_above.sum() / n_ex * 100 if n_ex > 0 else np.nan

    spread = ex_breadth - total_breadth
    return round(float(spread), 2)


def flag_ex_dividend_window(
    ex_dates: dict,
    reference_date: pd.Timestamp,
    buffer_days: int = 1,
) -> dict:
    """
    reference_date ± buffer_days 내에 배당락일이 있는 종목 플래그.
    """
    flagged = {}
    window_start = reference_date - pd.Timedelta(days=buffer_days)
    window_end = reference_date + pd.Timedelta(days=buffer_days)

    for ticker, dates in ex_dates.items():
        for d in dates:
            dt = pd.Timestamp(d)
            if window_start <= dt <= window_end:
                flagged[ticker] = str(d)
                break

    return {
        "count": len(flagged),
        "tickers": flagged,
        "window": f"{window_start.date()} ~ {window_end.date()}",
    }


def estimate_icc(
    breadth_series: pd.Series,
    lag: int = 1,
) -> float:
    """
    breadth 시계열의 자기상관으로 ICC 근사 추정.
    """
    if len(breadth_series) < lag + 10:
        return np.nan
    clean = breadth_series.dropna()
    return round(float(clean.autocorr(lag=lag)), 4)
