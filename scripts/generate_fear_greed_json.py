#!/usr/bin/env python3
"""Generate live-but-lightweight Fear & Greed JSON outputs."""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from config import PRICE_COLUMN

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "apps" / "fear-greed" / "api"
BREADTH_LATEST_PATH = ROOT / "docs" / "breadth" / "api" / "latest.json"
LOOKBACK_PERIOD = "6mo"
RISK_TICKERS = {
    "SPY": "SPY",
    "VIX": "^VIX",
    "HYG": "HYG",
    "LQD": "LQD",
    "TLT": "TLT",
}
DOWNLOAD_PARAMS = {
    "period": LOOKBACK_PERIOD,
    "interval": "1d",
    "auto_adjust": False,
    "progress": False,
    "threads": False,
}


def _output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _extract_close_frame(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        raise RuntimeError("fear-greed prices download returned empty frame")

    if isinstance(raw.columns, pd.MultiIndex):
        if PRICE_COLUMN in raw.columns.get_level_values(0):
            close = raw[PRICE_COLUMN].copy()
        else:
            close = raw.xs(raw.columns.levels[0][0], axis=1, level=0).copy()
    else:
        close = raw.copy()

    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])
    elif len(tickers) == 1 and tickers[0] not in close.columns:
        close.columns = [tickers[0]]

    return close.sort_index()


def fetch_risk_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker in RISK_TICKERS.values():
        try:
            raw = yf.download(tickers=ticker, **DOWNLOAD_PARAMS)
            close = _extract_close_frame(raw, [ticker])
            frames.append(close)
        except Exception as exc:
            logger.warning("fear-greed download failed for %s: %s", ticker, exc)

    if not frames:
        raise RuntimeError("fear-greed prices download returned empty frame")

    combined = pd.concat(frames, axis=1).sort_index()
    logger.info("fear-greed download complete: %s", ", ".join(combined.columns))
    return combined


def load_breadth_snapshot(path: Path = BREADTH_LATEST_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"breadth snapshot not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: float | int | np.floating | None) -> float | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _clamp_score(value: float | None) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(np.clip(value, 0, 100)), 2)


def _rolling_z_series(series: pd.Series, window: int = 20) -> pd.Series:
    mean = series.rolling(window=window, min_periods=max(10, window // 2)).mean()
    std = series.rolling(window=window, min_periods=max(10, window // 2)).std(ddof=0)
    z = (series - mean) / std.replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def _score_from_z_series(series: pd.Series, invert: bool = False) -> pd.Series:
    z = _rolling_z_series(series)
    if invert:
        z = -z
    score = 50 + (z * 15)
    return score.clip(lower=0, upper=100)


def _latest_and_previous(series: pd.Series) -> tuple[float | None, float | None]:
    clean = series.dropna()
    if clean.empty:
      return None, None
    latest = float(clean.iloc[-1])
    previous = float(clean.iloc[-2]) if len(clean) >= 2 else None
    return latest, previous


def _breadth_score_snapshot(breadth_latest: dict) -> tuple[float | None, float | None, str | None]:
    latest_values: list[float] = []
    previous_values: list[float] = []
    as_of_dates: list[str] = []

    for market_id in ("sp500", "nikkei225", "kospi200"):
        market = breadth_latest.get(market_id, {})
        if market.get("status") != "ok" or not market.get("series_valid"):
            continue
        breadth_50 = market.get("breadth_50")
        if breadth_50 is not None:
            latest_values.append(float(breadth_50))
        series = market.get("timeseries_50") or []
        valid_points = [row for row in series if row.get("value") is not None]
        if len(valid_points) >= 2:
            previous_values.append(float(valid_points[-2]["value"]))
        as_of = market.get("as_of_date")
        if as_of:
            as_of_dates.append(as_of)

    latest = float(np.mean(latest_values)) if latest_values else None
    previous = float(np.mean(previous_values)) if previous_values else None
    as_of_date = max(as_of_dates) if as_of_dates else None
    return latest, previous, as_of_date


def _score_label(score: float | None) -> str | None:
    if score is None:
        return None
    if score < 20:
        return "extreme_fear"
    if score < 40:
        return "fear"
    if score < 60:
        return "neutral"
    if score < 80:
        return "greed"
    return "extreme_greed"


def _contrarian_bias(score: float | None) -> str:
    if score is None:
        return "neutral"
    if score <= 35:
        return "risk_on"
    if score >= 65:
        return "risk_off"
    return "neutral"


def _build_component_scores(prices: pd.DataFrame, breadth_latest: dict) -> tuple[dict, dict]:
    inputs: dict[str, float | None] = {}
    previous_inputs: dict[str, float | None] = {}
    as_of_dates: list[str] = []

    if "SPY" in prices.columns:
        momentum_series = _score_from_z_series(prices["SPY"])
        inputs["momentum"], previous_inputs["momentum"] = _latest_and_previous(momentum_series)
        if not prices["SPY"].dropna().empty:
            as_of_dates.append(prices["SPY"].dropna().index[-1].strftime("%Y-%m-%d"))
    else:
        inputs["momentum"] = previous_inputs["momentum"] = None

    if "^VIX" in prices.columns:
        volatility_series = _score_from_z_series(prices["^VIX"], invert=True)
        inputs["volatility"], previous_inputs["volatility"] = _latest_and_previous(volatility_series)
        if not prices["^VIX"].dropna().empty:
            as_of_dates.append(prices["^VIX"].dropna().index[-1].strftime("%Y-%m-%d"))
    else:
        inputs["volatility"] = previous_inputs["volatility"] = None

    if {"HYG", "LQD"}.issubset(prices.columns):
        credit_ratio = prices["HYG"] / prices["LQD"]
        credit_series = _score_from_z_series(credit_ratio)
        inputs["credit"], previous_inputs["credit"] = _latest_and_previous(credit_series)
    else:
        inputs["credit"] = previous_inputs["credit"] = None

    breadth_latest_score, breadth_previous_score, breadth_as_of = _breadth_score_snapshot(breadth_latest)
    inputs["breadth"] = breadth_latest_score
    previous_inputs["breadth"] = breadth_previous_score
    if breadth_as_of:
        as_of_dates.append(breadth_as_of)

    if {"SPY", "TLT"}.issubset(prices.columns):
        ratio = prices["SPY"] / prices["TLT"]
        safe_haven_series = _score_from_z_series(ratio)
        inputs["safe_haven_flow"], previous_inputs["safe_haven_flow"] = _latest_and_previous(safe_haven_series)
    else:
        inputs["safe_haven_flow"] = previous_inputs["safe_haven_flow"] = None

    return (
        {key: _clamp_score(value) for key, value in inputs.items()},
        {
            "previous_inputs": {key: _clamp_score(value) for key, value in previous_inputs.items()},
            "as_of_date": max(as_of_dates) if as_of_dates else None,
        },
    )


def build_fear_greed_payload(prices: pd.DataFrame, breadth_latest: dict) -> tuple[dict, dict]:
    inputs, extras = _build_component_scores(prices, breadth_latest)
    previous_inputs = extras["previous_inputs"]
    as_of_date = extras["as_of_date"]

    input_values = [value for value in inputs.values() if value is not None]
    previous_values = [value for value in previous_inputs.values() if value is not None]
    score_value = round(float(np.mean(input_values)), 2) if input_values else None
    previous_score = round(float(np.mean(previous_values)), 2) if previous_values else None
    label = _score_label(score_value)
    previous_label = _score_label(previous_score)
    z_score = round((score_value - 50.0) / 15.0, 4) if score_value is not None else None

    valid_inputs = len(input_values)
    if valid_inputs == len(inputs):
        status = "ok"
        error_code = None
        error_message = None
    elif valid_inputs >= 3:
        status = "partial"
        error_code = "partial_input_coverage"
        error_message = "Some Fear & Greed inputs are unavailable."
    else:
        status = "error"
        error_code = "insufficient_input_coverage"
        error_message = "Fear & Greed inputs are unavailable."

    latest = {
        "date": dt.date.today().isoformat(),
        "pipeline_date": dt.date.today().isoformat(),
        "app_id": "fear-greed",
        "status": status,
        "as_of_date": as_of_date,
        "series_valid": status == "ok",
        "metrics_valid": status in {"ok", "partial"} and score_value is not None,
        "error_code": error_code,
        "error_message": error_message,
        "score": {
            "value": score_value,
            "label": label,
            "z_score": _safe_float(z_score),
        },
        "inputs": inputs,
        "signals": {
            "contrarian_bias": _contrarian_bias(score_value),
            "turning_point_alert": bool(
                score_value is not None
                and previous_score is not None
                and previous_label is not None
                and label is not None
                and label != previous_label
                and abs(score_value - previous_score) >= 8
            ),
        },
        "data_source": {
            "primary": "yfinance+breadth",
            "tickers": RISK_TICKERS,
            "period": LOOKBACK_PERIOD,
            "breadth_snapshot": str(BREADTH_LATEST_PATH.relative_to(ROOT)),
        },
        "widget_path": "/fear-greed",
        "dashboard_path": "/fear-greed/dashboard",
        "api_base": "/fear-greed/api",
    }

    metadata = {
        "app_id": "fear-greed",
        "app_name": "Fear & Greed",
        "status_contract": {
            "status": latest["status"],
            "as_of_date": latest["as_of_date"],
            "series_valid": latest["series_valid"],
            "metrics_valid": latest["metrics_valid"],
            "error_code": latest["error_code"],
            "error_message": latest["error_message"],
        },
        "paths": {
            "widget": latest["widget_path"],
            "dashboard": latest["dashboard_path"],
            "api_base": latest["api_base"],
        },
        "inputs": {
            "momentum": "SPY trend z-score normalized to 0-100.",
            "volatility": "Inverted VIX z-score normalized to 0-100.",
            "credit": "HYG/LQD relative-strength z-score normalized to 0-100.",
            "breadth": "Average breadth_50 across tracked equity markets.",
            "safe_haven_flow": "SPY/TLT ratio z-score normalized to 0-100.",
        },
        "data_source": latest["data_source"],
    }

    return latest, metadata


def write_fear_greed_payload(latest: dict, metadata: dict) -> None:
    out_dir = _output_dir()
    (out_dir / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("fear-greed payload written to %s", out_dir)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    prices = fetch_risk_prices()
    breadth_latest = load_breadth_snapshot()
    latest, metadata = build_fear_greed_payload(prices, breadth_latest)
    write_fear_greed_payload(latest, metadata)


if __name__ == "__main__":
    main()
