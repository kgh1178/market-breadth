"""전략 신호 생성 + 적중률 계산"""
import logging

import numpy as np
from scipy import stats as sp_stats

log = logging.getLogger(__name__)

# NOTE: 2026-03 breadth 재보정 완료.
# 아래 임계값은 split-only adjusted 기준.
# 기존 dividend-adjusted 기준 대비 breadth가 약 3-8pp 낮게 산출됨.
# 향후 신호 임계값을 조정할 때도 반드시 Close(split-only) 기준으로 검토.

ALL_MARKETS = ["sp500", "nikkei225", "kospi200"]


def wilson_ci(successes: int, trials: int,
              alpha: float = 0.05) -> dict:
    """Wilson 신뢰구간 계산"""
    if trials == 0:
        return {"hit_rate": 0, "ci_lower": 0, "ci_upper": 0,
                "n_trials": 0, "insufficient": True}
    z = sp_stats.norm.ppf(1 - alpha / 2)
    p_hat = successes / trials
    denom = 1 + z**2 / trials
    center = (p_hat + z**2 / (2 * trials)) / denom
    spread = z * np.sqrt(
        (p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials) / denom
    return {
        "hit_rate": round(p_hat * 100, 1),
        "ci_lower": round(max(0, (center - spread)) * 100, 1),
        "ci_upper": round(min(1, (center + spread)) * 100, 1),
        "n_trials": trials,
        "insufficient": trials < 5,
    }


def _missing_markets(latest: dict, required_markets: list[str]) -> list[str]:
    return [
        market for market in required_markets
        if not latest.get(market, {}).get("metrics_valid", False)
    ]


def _invalid_signal(strategy: str, required_markets: list[str],
                    reason: str, missing_markets: list[str]) -> dict:
    return {
        "strategy": strategy,
        "valid": False,
        "required_markets": required_markets,
        "missing_markets": missing_markets,
        "invalid_reason": reason,
        "direction": "UNAVAILABLE",
        "hit_rate_252d": None,
    }


def _decorate_signal(signal: dict, required_markets: list[str]) -> dict:
    signal["valid"] = True
    signal["required_markets"] = required_markets
    signal["missing_markets"] = []
    signal["invalid_reason"] = None
    return signal


def _asia_us_lead_signal(latest: dict) -> dict:
    """전략 1: Asia-US Lead-Lag"""
    required_markets = ALL_MARKETS
    missing_markets = _missing_markets(latest, required_markets)
    if missing_markets:
        return _invalid_signal(
            "asia_us_lead", required_markets,
            "missing_market_data", missing_markets)

    signal = {"strategy": "asia_us_lead", "direction": "NEUTRAL",
              "trigger_value": 0.0, "filter_passed": False,
              "hit_rate_252d": None}
    try:
        nk_50 = latest.get("nikkei225", {}).get("breadth_50")
        ks_50 = latest.get("kospi200", {}).get("breadth_50")
        sp_200 = latest.get("sp500", {}).get("breadth_200")

        asia_avg = (nk_50 + ks_50) / 2

        signal["trigger_value"] = round(asia_avg, 2)
        signal["filter_passed"] = sp_200 >= 40

        if asia_avg >= 70 and signal["filter_passed"]:
            signal["direction"] = "LONG"
        elif asia_avg <= 30 and signal["filter_passed"]:
            signal["direction"] = "SHORT"

        signal["hit_rate_252d"] = wilson_ci(0, 0)
    except Exception as e:
        log.warning(f"Asia-US Lead signal error: {e}")
        return _invalid_signal(
            "asia_us_lead", required_markets,
            "signal_calculation_failed", required_markets)
    return _decorate_signal(signal, required_markets)


def _tri_market_deviation_signal(latest: dict) -> dict:
    """전략 2: Tri-Market Deviation"""
    required_markets = ALL_MARKETS
    missing_markets = _missing_markets(latest, required_markets)
    if missing_markets:
        return _invalid_signal(
            "tri_market_deviation", required_markets,
            "missing_market_data", missing_markets)

    signal = {"strategy": "tri_market_deviation",
              "outlier_market": None, "z_deviation": 0.0,
              "direction": "NEUTRAL", "hit_rate_252d": None}
    try:
        z_scores = {}
        for mkt in required_markets:
            z_scores[mkt] = latest.get(mkt, {}).get("logit_z_50")

        mean_z = np.mean(list(z_scores.values()))
        max_dev_mkt = max(z_scores, key=lambda k: abs(z_scores[k] - mean_z))
        deviation = z_scores[max_dev_mkt] - mean_z

        if abs(deviation) >= 1.5:
            signal["outlier_market"] = max_dev_mkt
            signal["z_deviation"] = round(deviation, 3)
            signal["direction"] = "SHORT" if deviation > 0 else "LONG"

        signal["hit_rate_252d"] = wilson_ci(0, 0)
    except Exception as e:
        log.warning(f"Tri-Market Deviation signal error: {e}")
        return _invalid_signal(
            "tri_market_deviation", required_markets,
            "signal_calculation_failed", required_markets)
    return _decorate_signal(signal, required_markets)


def _regime_overlay_signal(latest: dict) -> dict:
    """전략 3: Regime-Switch Overlay"""
    required_markets = ALL_MARKETS
    missing_markets = _missing_markets(latest, required_markets)
    if missing_markets:
        return _invalid_signal(
            "regime_overlay", required_markets,
            "missing_market_data", missing_markets)

    signal = {"strategy": "regime_overlay",
              "grs_raw": 0.0, "regime": "SELECTIVE",
              "equity_weight_pct": 60, "hit_rate_252d": None}
    try:
        breadth_200 = [
            latest.get(mkt, {}).get("breadth_200") for mkt in required_markets
        ]

        grs = np.mean(breadth_200)
        signal["grs_raw"] = round(grs, 2)

        if grs >= 65:
            signal["regime"] = "BULL"
            signal["equity_weight_pct"] = 80
        elif grs >= 45:
            signal["regime"] = "SELECTIVE"
            signal["equity_weight_pct"] = 60
        elif grs >= 30:
            signal["regime"] = "TRANSITION"
            signal["equity_weight_pct"] = 40
        else:
            signal["regime"] = "BEAR"
            signal["equity_weight_pct"] = 30

        signal["hit_rate_252d"] = wilson_ci(0, 0)
    except Exception as e:
        log.warning(f"Regime Overlay signal error: {e}")
        return _invalid_signal(
            "regime_overlay", required_markets,
            "signal_calculation_failed", required_markets)
    return _decorate_signal(signal, required_markets)


ETF_MAP = {
    "sp500": {"long": "SPY", "short": "SH", "hedge": None},
    "nikkei225": {"long": "EWJ", "short": None, "hedge": "DXJ"},
    "kospi200": {"long": "EWY", "short": None, "hedge": "HEWY"},
}


def generate_signals(latest: dict) -> dict:
    """3개 전략 신호 + ETF 매핑 통합 생성"""
    signals = {
        "asia_us_lead": _asia_us_lead_signal(latest),
        "tri_market_deviation": _tri_market_deviation_signal(latest),
        "regime_overlay": _regime_overlay_signal(latest),
    }
    return {
        "date": latest.get("date", ""),
        "partial_data": any(not signal["valid"] for signal in signals.values()),
        "signals": signals,
        "etf_map": ETF_MAP,
        "reference": {
            "hlz_threshold": 3.0,
            "hlz_citation": ("Harvey, Liu, Zhu (2016). '...and the "
                             "Cross-Section of Expected Returns.' "
                             "Review of Financial Studies 29(1):5-68."),
            "note": ("hit_rate_252d requires historical time-series "
                     "backtest; placeholder values shown for daily "
                     "snapshot mode."),
        }
    }
