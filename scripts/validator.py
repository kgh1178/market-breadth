"""
Market Breadth — Validator
==========================
v3.1  2026-03-31  Fix: tolerance 3pp, n_valid 로깅, 시계열 검증
"""

import logging
import re
from typing import Optional

import numpy as np
import pandas as pd
import requests

from config import MAX_RMSE_PP, MIN_CORRELATION, VALIDATION_TOLERANCE_PP

logger = logging.getLogger(__name__)

MACROMICRO_SP500_50 = "https://en.macromicro.me/series/18331/sp500-50ma-breadth"
MACROMICRO_NIKKEI_200 = "https://en.macromicro.me/series/31801/japan-nikkei-225-200ma-breadth"


def _scrape_macromicro_value(url: str) -> Optional[float]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BreadthBot/3.1)"},
            timeout=15,
        )
        if not resp.ok:
            return None
        patterns = [
            r'"last_value":\s*([\d.]+)',
            r'"value":\s*([\d.]+)',
            r'<span[^>]*class="[^"]*last-value[^"]*"[^>]*>([\d.]+)',
        ]
        for pat in patterns:
            match = re.search(pat, resp.text)
            if match:
                return float(match.group(1))
    except Exception as exc:
        logger.debug("MacroMicro 스크레이핑 실패 (%s): %s", url, exc)
    return None


def validate_sp500_breadth(
    computed_50: float,
    computed_200: float,
    n_valid: int,
    n_total: int,
    tolerance_pp: float = VALIDATION_TOLERANCE_PP,
) -> dict:
    result = {
        "market": "sp500",
        "computed_50": computed_50,
        "computed_200": computed_200,
        "n_valid": n_valid,
        "n_total": n_total,
        "official_50": None,
        "diff_50": None,
        "pass_50": None,
        "source": None,
    }

    official = _scrape_macromicro_value(MACROMICRO_SP500_50)
    if official is not None:
        result["official_50"] = official
        result["source"] = "MacroMicro"
        diff = abs(computed_50 - official)
        result["diff_50"] = round(diff, 2)
        result["pass_50"] = diff <= tolerance_pp

        log_fn = logger.info if result["pass_50"] else logger.error
        log_fn(
            "[sp500] S5FI 검증 %s: computed=%.2f%% official=%.2f%% diff=%.2fpp n_valid=%s/%s",
            "통과" if result["pass_50"] else "실패",
            computed_50,
            official,
            diff,
            n_valid,
            n_total,
        )
    else:
        logger.warning("[sp500] 공식 S5FI 값 조회 실패. 스킵.")

    for label, val in [("50d", computed_50), ("200d", computed_200)]:
        result[f"range_check_{label}"] = val is None or 0 <= val <= 100
    return result


def validate_nikkei_breadth(
    computed_200: float,
    n_valid: int,
    n_total: int,
) -> dict:
    result = {
        "market": "nikkei225",
        "computed_200": computed_200,
        "n_valid": n_valid,
        "n_total": n_total,
        "official_200": None,
        "diff_200": None,
        "pass_200": None,
    }

    official = _scrape_macromicro_value(MACROMICRO_NIKKEI_200)
    if official is not None:
        result["official_200"] = official
        diff = abs(computed_200 - official)
        result["diff_200"] = round(diff, 2)
        result["pass_200"] = diff <= VALIDATION_TOLERANCE_PP
        log_fn = logger.info if result["pass_200"] else logger.error
        log_fn("[nikkei225] 검증 %s: diff=%.2fpp", "통과" if result["pass_200"] else "실패", diff)

    return result


def validate_internal_consistency(
    breadth_50: float,
    breadth_200: float,
) -> dict:
    return {
        "breadth_50_range": 0 <= (breadth_50 or 0) <= 100,
        "breadth_200_range": 0 <= (breadth_200 or 0) <= 100,
        "short_term_stronger": (breadth_50 or 0) >= (breadth_200 or 0),
    }


def run_timeseries_validation(
    our_series: pd.Series,
    official_series: pd.Series,
    min_correlation: float = MIN_CORRELATION,
    max_rmse_pp: float = MAX_RMSE_PP,
) -> dict:
    aligned = pd.concat(
        [our_series.rename("ours"), official_series.rename("official")],
        axis=1,
    ).dropna()

    if len(aligned) < 20:
        return {"status": "insufficient_data", "n": len(aligned)}

    corr = float(aligned["ours"].corr(aligned["official"]))
    rmse = float(np.sqrt(((aligned["ours"] - aligned["official"]) ** 2).mean()))
    bias = float((aligned["ours"] - aligned["official"]).mean())

    return {
        "status": "completed",
        "n": len(aligned),
        "correlation": round(corr, 4),
        "rmse_pp": round(rmse, 2),
        "bias_pp": round(bias, 2),
        "pass_corr": corr >= min_correlation,
        "pass_rmse": rmse <= max_rmse_pp,
        "pass": corr >= min_correlation and rmse <= max_rmse_pp,
    }
