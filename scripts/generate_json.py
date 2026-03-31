#!/usr/bin/env python3
"""
파이프라인 오케스트레이터.
구성종목 수집 → 가격 다운로드 → 브레드스 계산 → 정규화 → 검증 → 전략 → JSON 출력
"""

import datetime as dt
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from breadth_engine import (
    compute_breadth,
    compute_breadth_timeseries,
    compute_deff_ci,
    compute_ex_top5_spread,
    compute_pwds,
)
from config import MARKETS, MIN_COVERAGE_RATIO, OUTPUT_DIR, PRICE_COLUMN, YFINANCE_PARAMS
from fetchers import fetch_constituents, fetch_prices
from normalizer import causal_logit_zscore, composite_score, rolling_percentile
from strategy import generate_signals
from utils import is_any_market_open
from validator import (
    validate_internal_consistency,
    validate_nikkei_breadth,
    validate_sp500_breadth,
)

MA_WINDOWS = (50, 200)
PRICE_BASIS = "split-adjusted, dividend-unadjusted"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _output_dir() -> Path:
    return Path(OUTPUT_DIR)


def _structured_market_entry(
    *,
    status: str,
    as_of_date: Optional[str],
    series_valid: bool,
    metrics_valid: bool,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    extra: Optional[Dict] = None,
) -> dict:
    entry = {
        "status": status,
        "as_of_date": as_of_date,
        "series_valid": series_valid,
        "metrics_valid": metrics_valid,
        "error_code": error_code,
        "error_message": error_message,
    }
    if extra:
        entry.update(extra)
    return entry


def _remove_stale_series(market_id: str) -> None:
    ts_path = _output_dir() / f"{market_id}.json"
    if ts_path.exists():
        ts_path.unlink()
        logger.warning("Removed stale series file for %s: %s", market_id, ts_path)


def _infer_error_code(exc: Exception) -> str:
    msg = str(exc).lower()
    if "구성종목" in msg or "constituent" in msg or "wikipedia" in msg or "source" in msg:
        return "constituents_fetch_failed"
    if "price" in msg or "download" in msg or "coverage" in msg:
        return "prices_fetch_failed"
    return "calculation_failed"


def _coverage_error_message(market_id: str, coverage_pct: float) -> str:
    return (
        f"{market_id}: coverage {coverage_pct:.1f}% below minimum "
        f"{MIN_COVERAGE_RATIO * 100:.1f}%"
    )


def _downloaded_tickers(prices: pd.DataFrame) -> list[str]:
    if isinstance(prices.columns, pd.MultiIndex):
        if PRICE_COLUMN in prices.columns.get_level_values(0):
            return [str(col) for col in prices[PRICE_COLUMN].columns]
        return [str(col) for col in prices.columns.get_level_values(-1)]
    if PRICE_COLUMN in prices.columns:
        return [PRICE_COLUMN]
    return [str(col) for col in prices.columns]


def _ts_records(ts_df: pd.DataFrame) -> list[dict]:
    if ts_df.empty:
        return []
    clean = ts_df.dropna(subset=["breadth"]).copy()
    if clean.empty:
        return []
    return [
        {
            "date": row["date"],
            "value": row["breadth"],
            "n_above": int(row["n_above"]),
            "n_valid": int(row["n_valid"]),
        }
        for _, row in clean.iterrows()
    ]


def _compute_window_snapshot(
    prices: pd.DataFrame,
    window: int,
    icc_estimate: float,
) -> tuple[dict, dict, list[dict], float, float, float]:
    result = compute_breadth(prices, window=window)
    ci = compute_deff_ci(result["n_above"], result["n_valid"], icc_estimate)
    ts_df = compute_breadth_timeseries(prices, window=window)
    ts_records = _ts_records(ts_df)

    z_score = 0.0
    percentile = 50.0
    if len(ts_records) >= 60:
        breadth_series = pd.Series(
            [point["value"] for point in ts_records],
            index=pd.to_datetime([point["date"] for point in ts_records]),
        )
        z_score = float(causal_logit_zscore(breadth_series))
        percentile = float(rolling_percentile(breadth_series))

    composite = float(composite_score(z_score, percentile))
    return result, ci, ts_records, z_score, percentile, composite


def process_market(market_id: str) -> dict:
    """단일 마켓 처리."""
    cfg = MARKETS[market_id]

    tickers = fetch_constituents(market_id)
    prices = fetch_prices(tickers, market_id)

    if isinstance(prices.columns, pd.MultiIndex):
        assert PRICE_COLUMN in prices.columns.get_level_values(0), (
            f"'{PRICE_COLUMN}' 열이 없음. auto_adjust=False 확인 필요."
        )
        if "Adj Close" not in prices.columns.get_level_values(0):
            logger.warning(
                "Adj Close 열 부재 — auto_adjust=True가 적용된 것으로 의심됨! "
                "config.py의 YFINANCE_PARAMS 확인 필요."
            )

    downloaded = _downloaded_tickers(prices)
    coverage_ratio = (len(downloaded) / len(tickers)) if tickers else 0.0
    coverage_pct = round(coverage_ratio * 100, 1)
    failed_symbols = [ticker for ticker in tickers if ticker not in set(downloaded)]

    if coverage_ratio < MIN_COVERAGE_RATIO:
        raise RuntimeError(_coverage_error_message(market_id, coverage_pct))

    result_50, ci_50, ts_50, logit_z_50, percentile_50, composite_50 = _compute_window_snapshot(
        prices,
        window=50,
        icc_estimate=cfg.icc_estimate,
    )
    result_200, ci_200, ts_200, logit_z_200, percentile_200, composite_200 = _compute_window_snapshot(
        prices,
        window=200,
        icc_estimate=cfg.icc_estimate,
    )

    as_of_date = ts_50[-1]["date"] if ts_50 else (ts_200[-1]["date"] if ts_200 else None)

    if market_id == "sp500":
        validation = validate_sp500_breadth(
            computed_50=result_50["breadth"],
            computed_200=result_200["breadth"],
            n_valid=result_50["n_valid"],
            n_total=result_50["n_total"],
        )
    elif market_id == "nikkei225":
        validation = validate_nikkei_breadth(
            computed_200=result_200["breadth"],
            n_valid=result_200["n_valid"],
            n_total=result_200["n_total"],
        )
    else:
        validation = validate_internal_consistency(
            result_50["breadth"],
            result_200["breadth"],
        )

    market_json = {
        "market": cfg.name,
        "market_id": market_id,
        "breadth_50": result_50["breadth"],
        "breadth_200": result_200["breadth"],
        "n_above_50": result_50["n_above"],
        "n_above_200": result_200["n_above"],
        "count_above_50": result_50["n_above"],
        "count_above_200": result_200["n_above"],
        "n_valid_50": result_50["n_valid"],
        "n_valid_200": result_200["n_valid"],
        "n_total": result_50["n_total"],
        "n_total_50": result_50["n_total"],
        "n_total_200": result_200["n_total"],
        "n_excluded_50": result_50["n_excluded"],
        "n_excluded_200": result_200["n_excluded"],
        "ci_50": ci_50,
        "ci_200": ci_200,
        "ci_lower_50": ci_50["lower"],
        "ci_upper_50": ci_50["upper"],
        "ci_lower_200": ci_200["lower"],
        "ci_upper_200": ci_200["upper"],
        "deff_50": ci_50["deff"],
        "deff_200": ci_200["deff"],
        "n_eff_50": ci_50["n_eff"],
        "n_eff_200": ci_200["n_eff"],
        "timeseries_50": ts_50,
        "timeseries_200": ts_200,
        "breadth_series_50": ts_50,
        "breadth_series_200": ts_200,
        "validation": validation,
        "price_basis": PRICE_BASIS,
        "icc_estimate": cfg.icc_estimate,
        "estimated_icc": cfg.icc_estimate,
        "logit_z_50": round(logit_z_50, 3),
        "logit_z_200": round(logit_z_200, 3),
        "percentile_50": round(percentile_50, 1),
        "percentile_200": round(percentile_200, 1),
        "composite_50": round(composite_50, 3),
        "composite_200": round(composite_200, 3),
        "as_of_date": as_of_date,
        "coverage_pct": coverage_pct,
        "symbols_requested": len(tickers),
        "symbols_downloaded": len(downloaded),
        "failed_symbols": failed_symbols[:10],
        "ex_div_flag": False,
    }

    if "pwds" in cfg.special_metrics:
        market_json["pwds_50"] = compute_pwds(prices, window=50)
        market_json["pwds_200"] = compute_pwds(prices, window=200)
    if "ex_top5_spread" in cfg.special_metrics:
        market_json["ex_top5_spread_50"] = compute_ex_top5_spread(prices, window=50)
        market_json["ex_top5_spread_200"] = compute_ex_top5_spread(prices, window=200)

    return market_json


def build_metadata(results: dict) -> dict:
    return {
        "date": results["date"],
        "pipeline_date": results["pipeline_date"],
        "markets": results["markets"],
        "errors": results["errors"],
        "pipeline_duration_sec": results["pipeline_duration_sec"],
        "price_basis": "split-adjusted, dividend-unadjusted (Barchart S5FI compatible)",
        "yfinance_auto_adjust": YFINANCE_PARAMS.get("auto_adjust", False),
        "price_column": PRICE_COLUMN,
    }


def run() -> None:
    start_time = time.time()
    today = dt.date.today().isoformat()

    if not is_any_market_open():
        logger.info("All markets closed today, skipping pipeline.")
        sys.exit(0)

    out_dir = _output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    latest = {"date": today, "pipeline_date": today}
    metadata_state = {
        "date": today,
        "pipeline_date": today,
        "markets": {},
        "errors": [],
        "pipeline_duration_sec": None,
    }

    for market_id, cfg in MARKETS.items():
        logger.info("━━━ Processing %s ━━━", cfg.name)
        try:
            market_json = process_market(market_id)
            series_payload = {
                "market": market_json["market"],
                "market_id": market_json["market_id"],
                "as_of_date": market_json["as_of_date"],
                "price_basis": market_json["price_basis"],
                "breadth_50": market_json["timeseries_50"],
                "breadth_200": market_json["timeseries_200"],
            }
            (out_dir / f"{market_id}.json").write_text(
                json.dumps(series_payload, ensure_ascii=False, indent=2)
            )

            latest[market_id] = _structured_market_entry(
                status="ok",
                as_of_date=market_json["as_of_date"],
                series_valid=True,
                metrics_valid=True,
                extra=market_json,
            )
            metadata_state["markets"][market_id] = {
                "status": "ok",
                "as_of_date": market_json["as_of_date"],
                "symbols_requested": market_json["symbols_requested"],
                "symbols_downloaded": market_json["symbols_downloaded"],
                "coverage_pct": market_json["coverage_pct"],
                "failed_symbols": market_json["failed_symbols"],
                "validation": market_json["validation"],
                "price_basis": market_json["price_basis"],
            }
        except Exception as exc:
            error_message = str(exc)
            error_code = (
                "coverage_below_threshold"
                if "coverage" in error_message.lower()
                else _infer_error_code(exc)
            )
            status = "partial" if error_code == "coverage_below_threshold" else "error"
            _remove_stale_series(market_id)
            metadata_state["errors"].append({
                "market": market_id,
                "error_code": error_code,
                "error": error_message,
            })
            metadata_state["markets"][market_id] = {
                "status": status,
                "error_code": error_code,
                "error": error_message,
                "price_basis": PRICE_BASIS,
            }
            latest[market_id] = _structured_market_entry(
                status=status,
                as_of_date=None,
                series_valid=False,
                metrics_valid=False,
                error_code=error_code,
                error_message=error_message,
                extra={"price_basis": PRICE_BASIS},
            )
            logger.error("%s pipeline failed: %s", market_id, exc, exc_info=True)

    try:
        signals = generate_signals(latest)
        (out_dir / "signals.json").write_text(json.dumps(signals, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.error("Signal generation failed: %s", exc)
        metadata_state["errors"].append({"market": "signals", "error": str(exc)})

    metadata_state["pipeline_duration_sec"] = round(time.time() - start_time, 1)
    metadata = build_metadata(metadata_state)

    (out_dir / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2))
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
