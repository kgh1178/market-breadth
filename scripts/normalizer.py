"""인과적 정규화: logit-Z 및 롤링 백분위"""
import numpy as np
import pandas as pd

def causal_logit_zscore(breadth_series: pd.Series,
                        lookback: int = 252) -> float:
    """
    최신 시점의 인과적 logit-Z 점수.
    μ, σ는 t-1까지의 데이터만 사용 (.shift(1)).
    """
    p = breadth_series / 100.0
    p = p.clip(0.01, 0.99)
    logit = np.log(p / (1 - p))

    # 인과적: 현재 시점의 정규화 모수는 이전 시점까지만 사용
    mu = logit.rolling(window=lookback, min_periods=60).mean().shift(1)
    sigma = logit.rolling(window=lookback, min_periods=60).std().shift(1)

    z = (logit - mu) / sigma.replace(0, np.nan)
    return float(z.iloc[-1]) if not np.isnan(z.iloc[-1]) else 0.0

def causal_logit_zscore_series(breadth_series: pd.Series,
                               lookback: int = 252) -> pd.Series:
    """전체 시계열의 인과적 logit-Z"""
    p = breadth_series / 100.0
    p = p.clip(0.01, 0.99)
    logit = np.log(p / (1 - p))
    mu = logit.rolling(window=lookback, min_periods=60).mean().shift(1)
    sigma = logit.rolling(window=lookback, min_periods=60).std().shift(1)
    return (logit - mu) / sigma.replace(0, np.nan)

def rolling_percentile(breadth_series: pd.Series,
                       lookback: int = 252) -> float:
    """최신 시점의 인과적 롤링 백분위 (0-100)"""
    shifted = breadth_series.shift(1)
    current = breadth_series.iloc[-1]
    window = shifted.iloc[-lookback:]
    window = window.dropna()
    if len(window) < 60:
        return 50.0  # 데이터 부족 시 중립
    pctl = (window < current).sum() / len(window) * 100
    return float(pctl)

def rolling_percentile_series(breadth_series: pd.Series,
                              lookback: int = 252) -> pd.Series:
    """전체 시계열의 인과적 롤링 백분위"""
    result = pd.Series(index=breadth_series.index, dtype=float)
    for i in range(lookback, len(breadth_series)):
        window = breadth_series.iloc[max(0, i-lookback):i]  # t-1까지
        current = breadth_series.iloc[i]
        if len(window.dropna()) < 60:
            result.iloc[i] = 50.0
        else:
            result.iloc[i] = (window.dropna() < current).sum() / \
                             len(window.dropna()) * 100
    return result

def composite_score(z: float, pctl: float) -> float:
    """복합 정규화 점수: logit-Z와 백분위의 가중 평균"""
    return 0.5 * z + 0.5 * (pctl / 50.0 - 1.0)
