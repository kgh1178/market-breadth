#!/usr/bin/env python3
"""Generate placeholder-but-live exchange app JSON outputs."""

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
OUTPUT_DIR = ROOT / "apps" / "exchange" / "api"
LOOKBACK_PERIOD = "6mo"
FX_TICKERS = {
    "USDKRW": {
        "ticker": "USDKRW=X",
        "label": "USD/KRW",
        "quote": "KRW",
        "direction": 1.0,
    },
    "USDJPY": {
        "ticker": "USDJPY=X",
        "label": "USD/JPY",
        "quote": "JPY",
        "direction": 1.0,
    },
    "EURUSD": {
        "ticker": "EURUSD=X",
        "label": "EUR/USD",
        "quote": "USD",
        "direction": -1.0,
    },
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
        raise RuntimeError("exchange prices download returned empty frame")

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


def fetch_exchange_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for cfg in FX_TICKERS.values():
        ticker = cfg["ticker"]
        try:
            raw = yf.download(tickers=ticker, **DOWNLOAD_PARAMS)
            close = _extract_close_frame(raw, [ticker])
            frames.append(close)
        except Exception as exc:
            logger.warning("exchange download failed for %s: %s", ticker, exc)

    if not frames:
        raise RuntimeError("exchange prices download returned empty frame")

    combined = pd.concat(frames, axis=1).sort_index()
    logger.info("exchange download complete: %s", ", ".join(combined.columns))
    return combined


def _safe_float(value: float | int | np.floating | None) -> float | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _pair_snapshot(series: pd.Series) -> dict:
    clean = series.dropna()
    if len(clean) < 2:
        return {
            "value": None,
            "daily_change_pct": None,
            "z_score_20d": None,
            "as_of_date": None,
        }

    latest = float(clean.iloc[-1])
    prev = float(clean.iloc[-2])
    daily_change_pct = ((latest / prev) - 1.0) * 100.0 if prev else np.nan

    window = clean.iloc[-20:]
    z_score = np.nan
    if len(window) >= 10:
        std = window.std(ddof=0)
        if std and not np.isnan(std):
            z_score = (latest - window.mean()) / std

    return {
        "value": _safe_float(latest),
        "daily_change_pct": _safe_float(daily_change_pct),
        "z_score_20d": _safe_float(z_score),
        "as_of_date": clean.index[-1].strftime("%Y-%m-%d"),
    }


def _coverage_status(pair_payloads: dict[str, dict]) -> tuple[str, str | None, str | None]:
    valid_pairs = sum(1 for payload in pair_payloads.values() if payload["value"] is not None)
    if valid_pairs == len(pair_payloads):
        return "ok", None, None
    if valid_pairs > 0:
        return "partial", "partial_pair_coverage", "Some FX pairs are unavailable."
    return "error", "prices_fetch_failed", "All FX pairs are unavailable."


def _regime_from_pairs(pair_payloads: dict[str, dict]) -> dict:
    directional_scores = []
    asia_scores = []
    for pair_id, payload in pair_payloads.items():
        z_score = payload["z_score_20d"]
        if z_score is None:
            continue
        adjusted = z_score * FX_TICKERS[pair_id]["direction"]
        directional_scores.append(adjusted)
        if pair_id in {"USDKRW", "USDJPY"}:
            asia_scores.append(payload["z_score_20d"])

    usd_strength_score = float(np.mean(directional_scores)) if directional_scores else 0.0
    asia_pressure_score = float(np.mean(asia_scores)) if asia_scores else 0.0

    if usd_strength_score >= 0.75:
        usd_strength = "strong"
    elif usd_strength_score <= -0.75:
        usd_strength = "weak"
    else:
        usd_strength = "neutral"

    if asia_pressure_score >= 1.0:
        asia_fx_pressure = "high"
    elif asia_pressure_score >= 0.25:
        asia_fx_pressure = "medium"
    else:
        asia_fx_pressure = "low"

    return {
        "usd_strength": usd_strength,
        "asia_fx_pressure": asia_fx_pressure,
    }


def _signals_from_pairs(pair_payloads: dict[str, dict]) -> dict:
    krw = pair_payloads["USDKRW"]
    jpy = pair_payloads["USDJPY"]

    krw_alert = (
        (krw["z_score_20d"] is not None and krw["z_score_20d"] >= 1.5)
        or (krw["daily_change_pct"] is not None and krw["daily_change_pct"] >= 1.0)
    )
    yen_alert = (
        (jpy["z_score_20d"] is not None and abs(jpy["z_score_20d"]) >= 1.5)
        or (jpy["daily_change_pct"] is not None and abs(jpy["daily_change_pct"]) >= 1.0)
    )

    return {
        "krw_risk_alert": bool(krw_alert),
        "yen_breakout_alert": bool(yen_alert),
    }


def build_exchange_payload(prices: pd.DataFrame) -> tuple[dict, dict]:
    pair_payloads: dict[str, dict] = {}
    as_of_dates: list[str] = []

    for pair_id, cfg in FX_TICKERS.items():
        payload = _pair_snapshot(prices[cfg["ticker"]]) if cfg["ticker"] in prices.columns else _pair_snapshot(pd.Series(dtype=float))
        as_of = payload.pop("as_of_date")
        if as_of:
            as_of_dates.append(as_of)
        pair_payloads[pair_id] = payload

    status, error_code, error_message = _coverage_status(pair_payloads)
    as_of_date = max(as_of_dates) if as_of_dates else None
    regime = _regime_from_pairs(pair_payloads)
    signals = _signals_from_pairs(pair_payloads)

    latest = {
        "date": dt.date.today().isoformat(),
        "pipeline_date": dt.date.today().isoformat(),
        "app_id": "exchange",
        "status": status,
        "as_of_date": as_of_date,
        "series_valid": status == "ok",
        "metrics_valid": status in {"ok", "partial"},
        "error_code": error_code,
        "error_message": error_message,
        "pairs": pair_payloads,
        "regime": regime,
        "signals": signals,
        "data_source": {
            "primary": "yfinance",
            "tickers": {pair_id: cfg["ticker"] for pair_id, cfg in FX_TICKERS.items()},
            "period": LOOKBACK_PERIOD,
        },
        "widget_path": "/exchange",
        "dashboard_path": "/exchange/dashboard",
        "api_base": "/exchange/api",
    }

    metadata = {
        "app_id": "exchange",
        "app_name": "Exchange",
        "status_contract": {
            "status": status,
            "as_of_date": as_of_date,
            "series_valid": latest["series_valid"],
            "metrics_valid": latest["metrics_valid"],
            "error_code": error_code,
            "error_message": error_message,
        },
        "pairs": {
            pair_id: {
                "ticker": cfg["ticker"],
                "label": cfg["label"],
                "quote": cfg["quote"],
            }
            for pair_id, cfg in FX_TICKERS.items()
        },
        "signals_contract": {
            "krw_risk_alert": "USDKRW stress indicator based on z-score or daily move.",
            "yen_breakout_alert": "USDJPY breakout indicator based on z-score or daily move.",
        },
        "paths": {
            "widget": "/exchange",
            "dashboard": "/exchange/dashboard",
            "api_base": "/exchange/api",
        },
        "data_source": latest["data_source"],
    }
    return latest, metadata


def write_exchange_payload(latest: dict, metadata: dict) -> None:
    output_dir = _output_dir()
    (output_dir / "latest.json").write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    prices = fetch_exchange_prices()
    latest, metadata = build_exchange_payload(prices)
    write_exchange_payload(latest, metadata)
    logger.info("exchange payload written to %s", _output_dir())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
