#!/usr/bin/env python3
"""Generate multi-market Fear & Greed JSON outputs."""

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

MARKET_LABELS = {
    "us": "United States",
    "kr": "Korea",
    "jp": "Japan",
    "crypto": "Crypto",
}

RISK_TICKERS = {
    "SPY": "SPY",
    "VIX": "^VIX",
    "HYG": "HYG",
    "LQD": "LQD",
    "TLT": "TLT",
    "EWY": "EWY",
    "EWJ": "EWJ",
    "USDKRW": "USDKRW=X",
    "USDJPY": "USDJPY=X",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "GLD": "GLD",
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


def _extract_close_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw.empty:
        raise RuntimeError(f"fear-greed prices download returned empty frame for {ticker}")

    if isinstance(raw.columns, pd.MultiIndex):
        if PRICE_COLUMN in raw.columns.get_level_values(0):
            close = raw[PRICE_COLUMN].copy()
        else:
            close = raw.xs(raw.columns.levels[0][0], axis=1, level=0).copy()
    else:
        close = raw.copy()

    if isinstance(close, pd.Series):
        close = close.to_frame(name=ticker)
    elif ticker not in close.columns:
        close.columns = [ticker]

    return close.sort_index()


def fetch_risk_prices() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker in RISK_TICKERS.values():
        try:
            raw = yf.download(tickers=ticker, **DOWNLOAD_PARAMS)
            frames.append(_extract_close_frame(raw, ticker))
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


def _safe_float(value: float | int | np.floating | None, digits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


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


def _latest_as_of(series: pd.Series) -> str | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return clean.index[-1].strftime("%Y-%m-%d")


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


def _market_status(valid_count: int, total_count: int) -> tuple[str, str | None, str | None]:
    if valid_count == total_count and total_count > 0:
        return "ok", None, None
    if valid_count >= 3:
        return "partial", "partial_component_coverage", "Some market fear components are unavailable."
    return "error", "insufficient_component_coverage", "Market fear components are unavailable."


def _score_from_latest_previous(latest_values: dict[str, float | None], previous_values: dict[str, float | None]) -> tuple[float | None, float | None]:
    latest = [value for value in latest_values.values() if value is not None]
    previous = [value for value in previous_values.values() if value is not None]
    latest_score = round(float(np.mean(latest)), 2) if latest else None
    previous_score = round(float(np.mean(previous)), 2) if previous else None
    return latest_score, previous_score


def _market_payload(
    market_id: str,
    components: dict[str, float | None],
    previous_components: dict[str, float | None],
    as_of_dates: list[str],
) -> dict:
    score_value, previous_score = _score_from_latest_previous(components, previous_components)
    label = _score_label(score_value)
    previous_label = _score_label(previous_score)
    valid_count = sum(value is not None for value in components.values())
    status, error_code, error_message = _market_status(valid_count, len(components))
    z_score = round((score_value - 50.0) / 15.0, 4) if score_value is not None else None

    return {
        "status": status,
        "as_of_date": max(as_of_dates) if as_of_dates else None,
        "series_valid": status == "ok",
        "metrics_valid": status in {"ok", "partial"} and score_value is not None,
        "error_code": error_code,
        "error_message": error_message,
        "market": MARKET_LABELS[market_id],
        "market_id": market_id,
        "score": {
            "value": score_value,
            "label": label,
            "z_score": _safe_float(z_score),
        },
        "components": components,
        "signals": {
            "contrarian_bias": _contrarian_bias(score_value),
            "turning_point_alert": bool(
                score_value is not None
                and previous_score is not None
                and label is not None
                and previous_label is not None
                and label != previous_label
                and abs(score_value - previous_score) >= 8
            ),
        },
    }


def _breadth_component(breadth_latest: dict, market_key: str) -> tuple[float | None, float | None, str | None]:
    market = breadth_latest.get(market_key, {})
    if market.get("status") != "ok" or not market.get("series_valid"):
        return None, None, None

    latest = market.get("breadth_50")
    series = market.get("timeseries_50") or []
    valid_points = [row for row in series if row.get("value") is not None]
    previous = valid_points[-2]["value"] if len(valid_points) >= 2 else None
    return _clamp_score(latest), _clamp_score(previous), market.get("as_of_date")


def _score_series_avg(series_list: list[pd.Series]) -> pd.Series:
    frame = pd.concat(series_list, axis=1)
    return frame.mean(axis=1, skipna=True)


def _component_value(series: pd.Series, as_of_dates: list[str]) -> tuple[float | None, float | None]:
    as_of = _latest_as_of(series)
    if as_of:
        as_of_dates.append(as_of)
    latest, previous = _latest_and_previous(series)
    return _clamp_score(latest), _clamp_score(previous)


def _missing_component() -> tuple[float | None, float | None]:
    return None, None


def _percent_above_sma(close: pd.DataFrame, window: int = 50) -> pd.Series:
    sma = close.rolling(window=window, min_periods=window).mean()
    valid = close.notna() & sma.notna()
    above = (close > sma) & valid
    counts = valid.sum(axis=1)
    score = (above.sum(axis=1) / counts.replace(0, np.nan)) * 100
    return score


def _build_us_market(prices: pd.DataFrame, breadth_latest: dict) -> dict:
    as_of_dates: list[str] = []
    components: dict[str, float | None] = {}
    previous: dict[str, float | None] = {}

    if "SPY" in prices.columns:
        components["momentum"], previous["momentum"] = _component_value(_score_from_z_series(prices["SPY"]), as_of_dates)
    else:
        components["momentum"], previous["momentum"] = _missing_component()
    if "^VIX" in prices.columns:
        components["volatility"], previous["volatility"] = _component_value(_score_from_z_series(prices["^VIX"], invert=True), as_of_dates)
    else:
        components["volatility"], previous["volatility"] = _missing_component()
    if {"HYG", "LQD"}.issubset(prices.columns):
        credit_ratio = prices["HYG"] / prices["LQD"]
        components["credit"], previous["credit"] = _component_value(_score_from_z_series(credit_ratio), as_of_dates)
    else:
        components["credit"], previous["credit"] = _missing_component()
    breadth_latest_value, breadth_previous, breadth_as_of = _breadth_component(breadth_latest, "sp500")
    components["breadth"] = breadth_latest_value
    previous["breadth"] = breadth_previous
    if breadth_as_of:
        as_of_dates.append(breadth_as_of)
    if {"SPY", "TLT"}.issubset(prices.columns):
        safe_haven_ratio = prices["SPY"] / prices["TLT"]
        components["safe_haven_flow"], previous["safe_haven_flow"] = _component_value(_score_from_z_series(safe_haven_ratio), as_of_dates)
    else:
        components["safe_haven_flow"], previous["safe_haven_flow"] = _missing_component()

    return _market_payload("us", components, previous, as_of_dates)


def _build_kr_market(prices: pd.DataFrame, breadth_latest: dict) -> dict:
    as_of_dates: list[str] = []
    components: dict[str, float | None] = {}
    previous: dict[str, float | None] = {}

    if "EWY" in prices.columns:
        components["momentum"], previous["momentum"] = _component_value(_score_from_z_series(prices["EWY"]), as_of_dates)
    else:
        components["momentum"], previous["momentum"] = _missing_component()
    if "USDKRW=X" in prices.columns:
        components["fx_stress"], previous["fx_stress"] = _component_value(_score_from_z_series(prices["USDKRW=X"], invert=True), as_of_dates)
    else:
        components["fx_stress"], previous["fx_stress"] = _missing_component()
    breadth_latest_value, breadth_previous, breadth_as_of = _breadth_component(breadth_latest, "kospi200")
    components["breadth"] = breadth_latest_value
    previous["breadth"] = breadth_previous
    if breadth_as_of:
        as_of_dates.append(breadth_as_of)
    if {"EWY", "SPY"}.issubset(prices.columns):
        rel_strength = prices["EWY"] / prices["SPY"]
        components["relative_strength"], previous["relative_strength"] = _component_value(_score_from_z_series(rel_strength), as_of_dates)
    else:
        components["relative_strength"], previous["relative_strength"] = _missing_component()
    if {"EWY", "TLT"}.issubset(prices.columns):
        safe_haven_ratio = prices["EWY"] / prices["TLT"]
        components["safe_haven_flow"], previous["safe_haven_flow"] = _component_value(_score_from_z_series(safe_haven_ratio), as_of_dates)
    else:
        components["safe_haven_flow"], previous["safe_haven_flow"] = _missing_component()

    return _market_payload("kr", components, previous, as_of_dates)


def _build_jp_market(prices: pd.DataFrame, breadth_latest: dict) -> dict:
    as_of_dates: list[str] = []
    components: dict[str, float | None] = {}
    previous: dict[str, float | None] = {}

    if "EWJ" in prices.columns:
        components["momentum"], previous["momentum"] = _component_value(_score_from_z_series(prices["EWJ"]), as_of_dates)
    else:
        components["momentum"], previous["momentum"] = _missing_component()
    if "USDJPY=X" in prices.columns:
        components["fx_stress"], previous["fx_stress"] = _component_value(_score_from_z_series(prices["USDJPY=X"]), as_of_dates)
    else:
        components["fx_stress"], previous["fx_stress"] = _missing_component()
    breadth_latest_value, breadth_previous, breadth_as_of = _breadth_component(breadth_latest, "nikkei225")
    components["breadth"] = breadth_latest_value
    previous["breadth"] = breadth_previous
    if breadth_as_of:
        as_of_dates.append(breadth_as_of)
    if {"EWJ", "SPY"}.issubset(prices.columns):
        rel_strength = prices["EWJ"] / prices["SPY"]
        components["relative_strength"], previous["relative_strength"] = _component_value(_score_from_z_series(rel_strength), as_of_dates)
    else:
        components["relative_strength"], previous["relative_strength"] = _missing_component()
    if {"EWJ", "TLT"}.issubset(prices.columns):
        safe_haven_ratio = prices["EWJ"] / prices["TLT"]
        components["safe_haven_flow"], previous["safe_haven_flow"] = _component_value(_score_from_z_series(safe_haven_ratio), as_of_dates)
    else:
        components["safe_haven_flow"], previous["safe_haven_flow"] = _missing_component()

    return _market_payload("jp", components, previous, as_of_dates)


def _build_crypto_market(prices: pd.DataFrame) -> dict:
    as_of_dates: list[str] = []
    components: dict[str, float | None] = {}
    previous: dict[str, float | None] = {}

    if {"BTC-USD", "ETH-USD"}.issubset(prices.columns):
        btc_momentum = _score_from_z_series(prices["BTC-USD"])
        eth_momentum = _score_from_z_series(prices["ETH-USD"])
        components["momentum"], previous["momentum"] = _component_value(_score_series_avg([btc_momentum, eth_momentum]), as_of_dates)

        crypto_composite = (prices["BTC-USD"] + prices["ETH-USD"]) / 2
        realized_vol = crypto_composite.pct_change().rolling(window=20, min_periods=10).std(ddof=0) * np.sqrt(20)
        components["volatility"], previous["volatility"] = _component_value(_score_from_z_series(realized_vol, invert=True), as_of_dates)

        crypto_close = prices[["BTC-USD", "ETH-USD"]].copy()
        components["breadth"], previous["breadth"] = _component_value(_percent_above_sma(crypto_close), as_of_dates)

        eth_btc_ratio = prices["ETH-USD"] / prices["BTC-USD"]
        components["relative_strength"], previous["relative_strength"] = _component_value(_score_from_z_series(eth_btc_ratio), as_of_dates)
    else:
        components["momentum"], previous["momentum"] = _missing_component()
        components["volatility"], previous["volatility"] = _missing_component()
        components["breadth"], previous["breadth"] = _missing_component()
        components["relative_strength"], previous["relative_strength"] = _missing_component()

    if {"BTC-USD", "GLD"}.issubset(prices.columns):
        safe_haven_ratio = prices["BTC-USD"] / prices["GLD"]
        components["safe_haven_flow"], previous["safe_haven_flow"] = _component_value(_score_from_z_series(safe_haven_ratio), as_of_dates)
    else:
        components["safe_haven_flow"], previous["safe_haven_flow"] = _missing_component()

    return _market_payload("crypto", components, previous, as_of_dates)


def build_fear_greed_payload(prices: pd.DataFrame, breadth_latest: dict) -> tuple[dict, dict]:
    markets = {
        "us": _build_us_market(prices, breadth_latest),
        "kr": _build_kr_market(prices, breadth_latest),
        "jp": _build_jp_market(prices, breadth_latest),
        "crypto": _build_crypto_market(prices),
    }

    market_statuses = [market["status"] for market in markets.values()]
    market_as_of_dates = [market["as_of_date"] for market in markets.values() if market.get("as_of_date")]
    if all(status == "ok" for status in market_statuses):
        status = "ok"
        error_code = None
        error_message = None
    elif any(status in {"ok", "partial"} for status in market_statuses):
        status = "partial"
        error_code = "partial_market_coverage"
        error_message = "Some market fear indices are unavailable."
    else:
        status = "error"
        error_code = "no_market_coverage"
        error_message = "Market fear indices are unavailable."

    latest = {
        "date": dt.date.today().isoformat(),
        "pipeline_date": dt.date.today().isoformat(),
        "app_id": "fear-greed",
        "status": status,
        "as_of_date": max(market_as_of_dates) if market_as_of_dates else None,
        "series_valid": status == "ok",
        "metrics_valid": any(market["metrics_valid"] for market in markets.values()),
        "error_code": error_code,
        "error_message": error_message,
        "markets": markets,
        "default_market": "us",
        "widget_path": "/fear-greed",
        "dashboard_path": "/fear-greed/dashboard",
        "api_base": "/fear-greed/api",
    }

    metadata = {
        "app_id": "fear-greed",
        "app_name": "Market Fear Index",
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
        "markets": {
            "us": {
                "market": MARKET_LABELS["us"],
                "components": {
                    "momentum": "SPY trend z-score normalized to 0-100.",
                    "volatility": "Inverted VIX z-score normalized to 0-100.",
                    "credit": "HYG/LQD relative-strength z-score normalized to 0-100.",
                    "breadth": "S&P 500 breadth_50 score.",
                    "safe_haven_flow": "SPY/TLT ratio z-score normalized to 0-100.",
                },
            },
            "kr": {
                "market": MARKET_LABELS["kr"],
                "components": {
                    "momentum": "EWY trend z-score normalized to 0-100.",
                    "fx_stress": "Inverted USDKRW z-score normalized to 0-100.",
                    "breadth": "KOSPI 200 breadth_50 score.",
                    "relative_strength": "EWY/SPY z-score normalized to 0-100.",
                    "safe_haven_flow": "EWY/TLT ratio z-score normalized to 0-100.",
                },
            },
            "jp": {
                "market": MARKET_LABELS["jp"],
                "components": {
                    "momentum": "EWJ trend z-score normalized to 0-100.",
                    "fx_stress": "USDJPY z-score using yen-strength-as-fear orientation.",
                    "breadth": "Nikkei 225 breadth_50 score.",
                    "relative_strength": "EWJ/SPY z-score normalized to 0-100.",
                    "safe_haven_flow": "EWJ/TLT ratio z-score normalized to 0-100.",
                },
            },
            "crypto": {
                "market": MARKET_LABELS["crypto"],
                "components": {
                    "momentum": "Average of BTC and ETH trend z-scores normalized to 0-100.",
                    "volatility": "Inverted realized 20d volatility of BTC/ETH composite.",
                    "breadth": "Percent of BTC and ETH above 50d SMA.",
                    "relative_strength": "ETH/BTC z-score normalized to 0-100.",
                    "safe_haven_flow": "BTC/GLD ratio z-score normalized to 0-100.",
                },
            },
        },
        "data_source": {
            "primary": "yfinance+breadth",
            "tickers": RISK_TICKERS,
            "period": LOOKBACK_PERIOD,
            "breadth_snapshot": str(BREADTH_LATEST_PATH.relative_to(ROOT)),
        },
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
