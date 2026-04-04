from pathlib import Path
import importlib.util
import json
import sys

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "generate_fear_greed_json.py"


def _load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("generate_fear_greed_json", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


generate_fear_greed_json = _load_module()


def _sample_prices() -> pd.DataFrame:
    periods = 70
    dates = pd.bdate_range("2026-01-02", periods=periods)
    return pd.DataFrame(
        {
            "SPY": np.linspace(580, 640, periods),
            "^VIX": np.linspace(22.0, 14.0, periods),
            "HYG": np.linspace(77.0, 80.5, periods),
            "LQD": np.linspace(107.5, 104.5, periods),
            "TLT": np.linspace(92.0, 88.0, periods),
            "EWY": np.linspace(56.0, 61.5, periods),
            "EWJ": np.linspace(74.0, 79.5, periods),
            "USDKRW=X": np.linspace(1430, 1360, periods),
            "USDJPY=X": np.linspace(149.5, 156.0, periods),
            "BTC-USD": np.linspace(89000, 120000, periods),
            "ETH-USD": np.linspace(3100, 4100, periods),
            "GLD": np.linspace(266.0, 271.0, periods),
        },
        index=dates,
    )


def _sample_breadth() -> dict:
    def mk_market(as_of: str, breadth_50: float, history: list[float]) -> dict:
        dates = pd.bdate_range("2026-04-01", periods=len(history))
        return {
            "status": "ok",
            "as_of_date": as_of,
            "series_valid": True,
            "metrics_valid": True,
            "breadth_50": breadth_50,
            "timeseries_50": [
                {"date": date.strftime("%Y-%m-%d"), "value": value}
                for date, value in zip(dates, history)
            ],
        }

    return {
        "sp500": mk_market("2026-04-03", 24.06, [30.2, 27.4, 24.06]),
        "nikkei225": mk_market("2026-04-03", 29.91, [33.0, 31.5, 29.91]),
        "kospi200": mk_market("2026-04-03", 32.66, [36.8, 34.7, 32.66]),
    }


def test_build_fear_greed_payload_produces_four_market_shape():
    latest, metadata = generate_fear_greed_json.build_fear_greed_payload(_sample_prices(), _sample_breadth())

    assert latest["app_id"] == "fear-greed"
    assert latest["default_market"] == "us"
    assert set(latest["markets"].keys()) == {"us", "kr", "jp", "crypto"}
    assert latest["status"] == "ok"

    for market_id in ("us", "kr", "jp", "crypto"):
        market = latest["markets"][market_id]
        assert {"status", "as_of_date", "series_valid", "metrics_valid", "market", "market_id", "score", "components", "signals"}.issubset(market.keys())
        assert market["status"] == "ok"
        assert market["market_id"] == market_id
        assert market["score"]["value"] is not None
        assert market["score"]["label"] in {"extreme_fear", "fear", "neutral", "greed", "extreme_greed"}
        assert market["signals"]["contrarian_bias"] in {"risk_on", "neutral", "risk_off"}

    assert metadata["app_name"] == "Market Fear Index"
    assert set(metadata["markets"].keys()) == {"us", "kr", "jp", "crypto"}


def test_build_fear_greed_payload_marks_partial_when_some_markets_fail():
    prices = _sample_prices().drop(columns=["EWY", "EWJ", "USDKRW=X", "USDJPY=X", "GLD"])
    breadth = _sample_breadth()
    breadth["kospi200"]["status"] = "error"
    breadth["kospi200"]["series_valid"] = False
    breadth["nikkei225"]["status"] = "error"
    breadth["nikkei225"]["series_valid"] = False

    latest, metadata = generate_fear_greed_json.build_fear_greed_payload(prices, breadth)

    assert latest["status"] == "partial"
    assert latest["series_valid"] is False
    assert latest["metrics_valid"] is True
    assert latest["error_code"] == "partial_market_coverage"
    assert latest["markets"]["us"]["status"] == "ok"
    assert latest["markets"]["kr"]["status"] in {"partial", "error"}
    assert latest["markets"]["jp"]["status"] == "error"
    assert metadata["status_contract"]["status"] == "partial"


def test_build_fear_greed_payload_marks_error_when_all_markets_fail():
    prices = _sample_prices()[["SPY"]].copy()
    breadth = {
        "sp500": {"status": "error", "series_valid": False},
        "nikkei225": {"status": "error", "series_valid": False},
        "kospi200": {"status": "error", "series_valid": False},
    }

    latest, _ = generate_fear_greed_json.build_fear_greed_payload(prices, breadth)

    assert latest["status"] == "error"
    assert latest["metrics_valid"] is False
    assert latest["error_code"] == "no_market_coverage"
    assert all(market["status"] == "error" for market in latest["markets"].values())


def test_crypto_market_uses_btc_eth_composite():
    latest, _ = generate_fear_greed_json.build_fear_greed_payload(_sample_prices(), _sample_breadth())
    crypto = latest["markets"]["crypto"]

    assert set(crypto["components"].keys()) == {
        "momentum",
        "volatility",
        "breadth",
        "relative_strength",
        "safe_haven_flow",
    }
    assert crypto["components"]["momentum"] is not None
    assert crypto["components"]["breadth"] is not None


def test_write_fear_greed_payload_writes_source_files(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_fear_greed_json, "OUTPUT_DIR", tmp_path)
    latest, metadata = generate_fear_greed_json.build_fear_greed_payload(_sample_prices(), _sample_breadth())

    generate_fear_greed_json.write_fear_greed_payload(latest, metadata)

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "metadata.json").exists()


def test_load_breadth_snapshot_reads_json(tmp_path):
    path = tmp_path / "latest.json"
    path.write_text(json.dumps(_sample_breadth()), encoding="utf-8")

    data = generate_fear_greed_json.load_breadth_snapshot(path)

    assert data["sp500"]["breadth_50"] == 24.06
