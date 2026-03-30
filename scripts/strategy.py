"""전략 신호 생성 + 적중률 계산"""
import numpy as np
from scipy import stats as sp_stats
import logging

log = logging.getLogger(__name__)

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

def _asia_us_lead_signal(latest: dict) -> dict:
    """전략 1: Asia-US Lead-Lag"""
    signal = {"strategy": "asia_us_lead", "direction": "NEUTRAL",
              "trigger_value": 0.0, "filter_passed": False,
              "hit_rate_252d": None}
    try:
        nk_50 = latest.get("nikkei225", {}).get("breadth_50", 50)
        ks_50 = latest.get("kospi200", {}).get("breadth_50", 50)
        sp_200 = latest.get("sp500", {}).get("breadth_200", 50)

        # 아시아 평균 50일 변화 (간이: 전일 대비는 시계열 필요)
        # 스냅샷에서는 절대 수준 기반 판단
        asia_avg = (nk_50 + ks_50) / 2

        signal["trigger_value"] = round(asia_avg, 2)
        signal["filter_passed"] = sp_200 >= 40

        if asia_avg >= 70 and signal["filter_passed"]:
            signal["direction"] = "LONG"
        elif asia_avg <= 30 and signal["filter_passed"]:
            signal["direction"] = "SHORT"

        # 적중률은 시계열 기반이므로 별도 백테스트에서 산출
        # 여기서는 placeholder
        signal["hit_rate_252d"] = wilson_ci(0, 0)
    except Exception as e:
        log.warning(f"Asia-US Lead signal error: {e}")
    return signal

def _tri_market_deviation_signal(latest: dict) -> dict:
    """전략 2: Tri-Market Deviation"""
    signal = {"strategy": "tri_market_deviation",
              "outlier_market": None, "z_deviation": 0.0,
              "direction": "NEUTRAL", "hit_rate_252d": None}
    try:
        z_scores = {}
        for mkt in ["sp500", "nikkei225", "kospi200"]:
            z = latest.get(mkt, {}).get("logit_z_50", 0)
            z_scores[mkt] = z

        if not z_scores:
            return signal

        mean_z = np.mean(list(z_scores.values()))
        max_dev_mkt = max(z_scores, key=lambda k: abs(z_scores[k] - mean_z))
        deviation = z_scores[max_dev_mkt] - mean_z

        if abs(deviation) >= 1.5:
            signal["outlier_market"] = max_dev_mkt
            signal["z_deviation"] = round(deviation, 3)
            # 괴리 시장이 과매수이면 SHORT, 과매도이면 LONG
            signal["direction"] = "SHORT" if deviation > 0 else "LONG"

        signal["hit_rate_252d"] = wilson_ci(0, 0)
    except Exception as e:
        log.warning(f"Tri-Market Deviation signal error: {e}")
    return signal

def _regime_overlay_signal(latest: dict) -> dict:
    """전략 3: Regime-Switch Overlay"""
    signal = {"strategy": "regime_overlay",
              "grs_raw": 0.0, "regime": "SELECTIVE",
              "equity_weight_pct": 60, "hit_rate_252d": None}
    try:
        breadth_200 = []
        for mkt in ["sp500", "nikkei225", "kospi200"]:
            b = latest.get(mkt, {}).get("breadth_200", 50)
            breadth_200.append(b)

        grs = np.mean(breadth_200)
        signal["grs_raw"] = round(grs, 2)

        # 체제 판단 (3일 연속 확인은 시계열 필요, 여기서는 즉시 판단)
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
    return signal

# ETF 매핑
ETF_MAP = {
    "sp500": {"long": "SPY", "short": "SH",
              "hedge": None},
    "nikkei225": {"long": "EWJ", "short": None,
                  "hedge": "DXJ"},   # DXJ = 엔화 헤지
    "kospi200": {"long": "EWY", "short": None,
                 "hedge": "HEWY"},   # HEWY = 원화 헤지
}

def generate_signals(latest: dict) -> dict:
    """3개 전략 신호 + ETF 매핑 통합 생성"""
    return {
        "date": latest.get("date", ""),
        "signals": {
            "asia_us_lead": _asia_us_lead_signal(latest),
            "tri_market_deviation": _tri_market_deviation_signal(latest),
            "regime_overlay": _regime_overlay_signal(latest),
        },
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
