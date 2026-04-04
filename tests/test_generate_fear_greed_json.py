from pathlib import Path
import importlib.util
import json
import sys

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
    dates = pd.bdate_range("2026-03-03", periods=24)
    return pd.DataFrame(
        {
            "SPY": [580, 582, 581, 584, 586, 587, 589, 590, 588, 592, 594, 596, 595, 598, 600, 603, 604, 606, 608, 610, 612, 613, 615, 618],
            "^VIX": [20.0, 19.6, 19.3, 19.1, 18.9, 18.7, 18.5, 18.2, 18.0, 17.8, 17.6, 17.3, 17.1, 16.9, 16.8, 16.7, 16.5, 16.2, 16.1, 15.9, 15.8, 15.6, 15.5, 15.4],
            "HYG": [77.0, 77.1, 77.2, 77.3, 77.5, 77.6, 77.7, 77.8, 77.9, 78.0, 78.2, 78.3, 78.4, 78.5, 78.6, 78.7, 78.8, 78.9, 79.0, 79.1, 79.2, 79.3, 79.5, 79.7],
            "LQD": [107.0, 106.9, 106.8, 106.8, 106.7, 106.6, 106.6, 106.5, 106.4, 106.4, 106.3, 106.2, 106.2, 106.1, 106.0, 106.0, 105.9, 105.8, 105.8, 105.7, 105.6, 105.6, 105.5, 105.4],
            "TLT": [91.0, 90.8, 90.7, 90.6, 90.4, 90.3, 90.2, 90.0, 89.9, 89.8, 89.7, 89.5, 89.4, 89.3, 89.2, 89.1, 89.0, 88.9, 88.8, 88.7, 88.6, 88.5, 88.4, 88.3],
        },
        index=dates,
    )


def _sample_breadth() -> dict:
    def mk_market(as_of: str, breadth_50: float, history: list[float]) -> dict:
        dates = pd.bdate_range("2026-03-30", periods=len(history))
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
        "sp500": mk_market("2026-04-03", 28.63, [24.1, 26.3, 28.63]),
        "nikkei225": mk_market("2026-04-03", 39.73, [35.0, 37.8, 39.73]),
        "kospi200": mk_market("2026-04-03", 29.15, [27.2, 28.0, 29.15]),
    }


def test_build_fear_greed_payload_produces_live_shape():
    latest, metadata = generate_fear_greed_json.build_fear_greed_payload(_sample_prices(), _sample_breadth())

    assert latest["app_id"] == "fear-greed"
    assert latest["status"] == "ok"
    assert latest["series_valid"] is True
    assert latest["metrics_valid"] is True
    assert latest["score"]["value"] is not None
    assert latest["score"]["label"] in {"extreme_fear", "fear", "neutral", "greed", "extreme_greed"}
    assert latest["inputs"]["momentum"] is not None
    assert latest["inputs"]["breadth"] is not None
    assert latest["signals"]["contrarian_bias"] in {"risk_on", "neutral", "risk_off"}
    assert metadata["data_source"]["primary"] == "yfinance+breadth"


def test_build_fear_greed_payload_marks_partial_when_inputs_missing():
    prices = _sample_prices().drop(columns=["TLT", "LQD"])
    breadth = _sample_breadth()
    breadth["nikkei225"]["status"] = "error"
    breadth["nikkei225"]["series_valid"] = False

    latest, metadata = generate_fear_greed_json.build_fear_greed_payload(prices, breadth)

    assert latest["status"] == "partial"
    assert latest["series_valid"] is False
    assert latest["metrics_valid"] is True
    assert latest["error_code"] == "partial_input_coverage"
    assert latest["inputs"]["credit"] is None
    assert metadata["status_contract"]["status"] == "partial"


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

    assert data["sp500"]["breadth_50"] == 28.63
