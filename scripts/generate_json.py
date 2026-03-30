#!/usr/bin/env python3
"""
파이프라인 오케스트레이터.
구성종목 수집 → 가격 다운로드 → 브레드스 계산 → 정규화 → 검증 → 전략 → JSON 출력
"""
import json
import pathlib
import datetime as dt
import time
import logging
import sys

from config import MARKETS, MA_WINDOWS, OUTPUT_DIR
from fetchers import fetch_constituents, fetch_prices
from breadth_engine import (
    compute_breadth, compute_breadth_timeseries, compute_deff_ci,
    flag_ex_dividend, compute_pwds, compute_ex_top5_spread,
    estimate_icc,
)
from normalizer import (
    causal_logit_zscore, rolling_percentile, composite_score,
)
from validator import (
    validate_against_s5fi, validate_against_macromicro,
    validate_internal_consistency,
)
from strategy import generate_signals
from utils import is_any_market_open

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
log = logging.getLogger(__name__)

def run():
    start_time = time.time()
    today = dt.date.today().isoformat()

    # ── 거래일 체크 ──
    if not is_any_market_open():
        log.info("All markets closed today, skipping pipeline.")
        sys.exit(0)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latest = {"date": today}
    metadata = {"date": today, "markets": {}, "errors": [],
                "pipeline_duration_sec": None}

    for mkt_id, cfg in MARKETS.items():
        log.info(f"━━━ Processing {cfg.name} ━━━")
        try:
            # 1. 구성종목
            symbols = fetch_constituents(cfg)

            # 2. 가격
            prices, failed, coverage = fetch_prices(symbols, cfg)

            # 3. 브레드스 (최신 스냅샷)
            result = {"n_active": 0}
            for window in MA_WINDOWS:
                b = compute_breadth(prices, window)
                ci = compute_deff_ci(
                    b["count_above"], b["n_active"], icc=cfg.estimated_icc)

                # 시계열에서 logit-Z, 백분위 계산
                ts = compute_breadth_timeseries(prices, [window], days=504)
                import pandas as pd
                blist = ts.get(f"breadth_{window}", [])
                if len(blist) >= 60:
                    bseries = pd.Series(
                        [d["value"] for d in blist],
                        index=pd.to_datetime([d["date"] for d in blist]))
                    z = causal_logit_zscore(bseries)
                    pctl = rolling_percentile(bseries)
                else:
                    z, pctl = 0.0, 50.0 # 기본값

                result[f"breadth_{window}"] = round(b["breadth_pct"], 2)
                result[f"count_above_{window}"] = b["count_above"]
                result[f"ci_lower_{window}"] = ci["lower"]
                result[f"ci_upper_{window}"] = ci["upper"]
                result[f"deff_{window}"] = ci["deff"]
                result[f"n_eff_{window}"] = ci["n_eff"]
                result[f"confidence_grade_{window}"] = ci["confidence_grade"]
                result[f"logit_z_{window}"] = round(z, 3)
                result[f"percentile_{window}"] = round(pctl, 1)
                result[f"composite_{window}"] = round(
                    composite_score(z, pctl), 3)
                result["n_active"] = b["n_active"]

            # 4. 시장별 특수 지표
            if "pwds" in cfg.special_metrics:
                result["pwds_50"] = round(compute_pwds(prices, 50), 2)
                result["pwds_200"] = round(compute_pwds(prices, 200), 2)
            if "ex_top5_spread" in cfg.special_metrics:
                result["ex_top5_spread_50"] = round(
                    compute_ex_top5_spread(prices, cfg, 50), 2)
                result["ex_top5_spread_200"] = round(
                    compute_ex_top5_spread(prices, cfg, 200), 2)

            # 5. 배당락 플래그
            result["ex_div_flag"] = flag_ex_dividend(today, cfg)

            # 6. ICC 재추정 (선택)
            result["estimated_icc"] = cfg.estimated_icc

            latest[mkt_id] = result

            # 7. 시계열 JSON (전체 윈도우)
            full_ts = compute_breadth_timeseries(prices, MA_WINDOWS, days=504)
            ts_path = OUTPUT_DIR / f"{mkt_id}.json"
            ts_path.write_text(json.dumps(full_ts, ensure_ascii=False))

            # 8. 검증
            val = {}
            if mkt_id == "sp500":
                val["s5fi"] = validate_against_s5fi(
                    result.get("breadth_50", 50))
            elif mkt_id == "nikkei225":
                val["macromicro"] = validate_against_macromicro(
                    result.get("breadth_200", 50))
            val["internal"] = validate_internal_consistency(
                result.get("breadth_50", 50), result.get("breadth_200", 50))

            metadata["markets"][mkt_id] = {
                "symbols_requested": len(symbols),
                "symbols_downloaded": len(prices.columns),
                "coverage_pct": round(coverage, 1),
                "status": "ok" if coverage >= 85 else "partial",
                "failed_symbols": failed[:10],  # 최대 10개만 기록
                "validation": val,
            }

        except Exception as e:
            log.error(f"{mkt_id} pipeline failed: {e}", exc_info=True)
            metadata["errors"].append({"market": mkt_id, "error": str(e)})
            latest[mkt_id] = {"error": str(e)}

    # ── 전략 신호 ──
    try:
        signals = generate_signals(latest)
        (OUTPUT_DIR / "signals.json").write_text(
            json.dumps(signals, ensure_ascii=False, indent=2))
    except Exception as e:
        log.error(f"Signal generation failed: {e}")
        metadata["errors"].append({"market": "signals", "error": str(e)})

    # ── 최종 출력 ──
    elapsed = round(time.time() - start_time, 1)
    metadata["pipeline_duration_sec"] = elapsed

    (OUTPUT_DIR / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2))
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2))

    n_files = len(list(OUTPUT_DIR.glob("*.json")))
    log.info(f"✅ Generated {n_files} JSON files in {elapsed}s")

    # 에러 존재 시 비정상 종료하지 않되, 경고 출력
    if metadata["errors"]:
        log.warning(f"⚠ {len(metadata['errors'])} error(s) occurred: "
                    f"{metadata['errors']}")

if __name__ == "__main__":
    run()
