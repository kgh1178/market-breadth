"""브레드스 계산, DEFF 신뢰구간, 시장별 특수 지표"""
import numpy as np
import pandas as pd
from scipy import stats
from config import MarketConfig

def compute_breadth(prices: pd.DataFrame, window: int) -> dict:
    """최신일 기준 브레드스 계산"""
    sma = prices.rolling(window=window, min_periods=window).mean()
    latest_price = prices.iloc[-1]
    latest_sma = sma.iloc[-1]
    # MA 윈도우 미달 종목 제외
    valid = latest_sma.notna()
    above = (latest_price[valid] > latest_sma[valid]).sum()
    n_active = valid.sum()
    breadth_pct = (above / n_active * 100) if n_active > 0 else np.nan
    return {"breadth_pct": float(breadth_pct),
            "count_above": int(above),
            "n_active": int(n_active)}

def compute_breadth_timeseries(prices: pd.DataFrame,
                                windows: list,
                                days: int = 504) -> dict:
    """최근 N일의 브레드스 시계열"""
    result = {}
    for w in windows:
        sma = prices.rolling(window=w, min_periods=w).mean()
        above_matrix = (prices > sma) & sma.notna()
        n_active = sma.notna().sum(axis=1)
        breadth = (above_matrix.sum(axis=1) / n_active * 100).dropna()
        breadth = breadth.tail(days)
        result[f"breadth_{w}"] = [
            {"date": d.strftime("%Y-%m-%d"), "value": round(v, 2)}
            for d, v in breadth.items()
        ]
    return result

def compute_deff_ci(k: int, n: int, icc: float,
                    alpha: float = 0.05) -> dict:
    """DEFF 보정 Clopper-Pearson 신뢰구간"""
    deff = 1 + (n - 1) * icc
    n_eff = max(n / deff, 2)  # 최소 2로 클리핑
    k_eff = round(k * n_eff / n)
    k_eff = max(0, min(k_eff, int(n_eff)))
    result = stats.binomtest(k_eff, int(round(n_eff)))
    ci = result.proportion_ci(confidence_level=1 - alpha, method='exact')
    grade = "A" if n_eff >= 30 else ("B" if n_eff >= 10 else "C")
    return {
        "lower": round(ci.low * 100, 2),
        "upper": round(ci.high * 100, 2),
        "deff": round(deff, 2),
        "n_eff": round(n_eff, 1),
        "confidence_grade": grade,
    }

def flag_ex_dividend(date_str: str, cfg: MarketConfig) -> bool:
    """배당락 시즌 윈도우 내 여부 확인"""
    import exchange_calendars as xcals
    from datetime import date, timedelta
    d = date.fromisoformat(date_str)
    if d.month not in cfg.ex_div_months:
        return False
    cal = xcals.get_calendar(cfg.exchange_cal_code)
    # 해당 월의 마지막 거래일
    month_end = date(d.year, d.month + 1, 1) - timedelta(days=1) \
                if d.month < 12 else date(d.year, 12, 31)
    sessions = cal.sessions_in_range(
        pd.Timestamp(d.year, d.month, 1),
        pd.Timestamp(month_end))
    if len(sessions) == 0:
        return False
    last_trading = sessions[-1].date()
    window_start = last_trading - timedelta(days=cfg.ex_div_window_days * 2)
    window_end = last_trading + timedelta(days=cfg.ex_div_window_days * 2)
    return window_start <= d <= window_end

def compute_pwds(prices: pd.DataFrame, window: int = 50) -> float:
    """Nikkei 가격가중괴리지표 (PWDS)"""
    sma = prices.rolling(window=window, min_periods=window).mean()
    latest_p = prices.iloc[-1]
    latest_sma = sma.iloc[-1]
    valid = latest_sma.notna()
    lp, ls = latest_p[valid], latest_sma[valid]
    above = (lp > ls)
    # 동일 가중 브레드스
    ew = above.mean() * 100
    # 가격 가중 브레드스
    weights = lp / lp.sum()
    pw = (weights * above.astype(float)).sum() * 100
    return float(ew - pw)

def compute_ex_top5_spread(prices: pd.DataFrame,
                           cfg: MarketConfig,
                           window: int = 50) -> float:
    """KOSPI 상위5종목 제외 브레드스 스프레드"""
    sma = prices.rolling(window=window, min_periods=window).mean()
    latest_p = prices.iloc[-1]
    latest_sma = sma.iloc[-1]
    valid = latest_sma.notna()
    lp, ls = latest_p[valid], latest_sma[valid]
    # 상위 5 종목 (최근 평균 가격 기준)
    avg20 = prices[valid.index].tail(20).mean()
    top5 = avg20.nlargest(5).index
    above_all = (lp > ls)
    above_ex = above_all.drop(top5, errors='ignore')
    full_breadth = above_all.mean() * 100
    ex_breadth = above_ex.mean() * 100
    return float(full_breadth - ex_breadth)

def estimate_icc(prices: pd.DataFrame, n_pairs: int = 100, seed: int = 42) -> float:
    """100개 무작위 쌍의 일일 수익률 상관계수 평균"""
    np.random.seed(seed)
    returns = prices.pct_change().dropna(how='all')
    cols = returns.columns.tolist()
    if len(cols) < 2:
        return 0.0
    
    corrs = []
    for _ in range(n_pairs):
        pair = np.random.choice(cols, 2, replace=False)
        corr = returns[pair[0]].corr(returns[pair[1]])
        if not np.isnan(corr):
            corrs.append(corr)
            
    return float(np.mean(corrs)) if corrs else 0.0
