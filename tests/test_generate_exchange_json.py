from pathlib import Path
import importlib.util
import sys

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "generate_exchange_json.py"


def _load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("generate_exchange_json", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


generate_exchange_json = _load_module()


def _sample_prices() -> pd.DataFrame:
    dates = pd.bdate_range("2026-03-03", periods=24)
    return pd.DataFrame(
        {
            "USDKRW=X": [1430, 1431, 1432, 1434, 1438, 1440, 1442, 1443, 1441, 1445, 1448, 1450, 1452, 1451, 1454, 1456, 1458, 1460, 1459, 1462, 1466, 1469, 1472, 1478],
            "USDJPY=X": [149.2, 149.1, 149.3, 149.4, 149.6, 149.8, 150.1, 150.0, 149.9, 150.2, 150.5, 150.8, 151.0, 150.7, 150.9, 151.2, 151.6, 151.8, 151.5, 151.9, 152.2, 152.4, 152.6, 153.1],
            "EURUSD=X": [1.088, 1.087, 1.086, 1.085, 1.084, 1.083, 1.082, 1.081, 1.082, 1.081, 1.080, 1.079, 1.078, 1.079, 1.078, 1.077, 1.076, 1.075, 1.074, 1.073, 1.072, 1.071, 1.070, 1.068],
        },
        index=dates,
    )


def test_build_exchange_payload_produces_live_shape():
    latest, metadata = generate_exchange_json.build_exchange_payload(_sample_prices())

    assert latest["app_id"] == "exchange"
    assert latest["status"] == "ok"
    assert latest["series_valid"] is True
    assert latest["metrics_valid"] is True
    assert latest["pairs"]["USDKRW"]["value"] is not None
    assert latest["pairs"]["USDJPY"]["daily_change_pct"] is not None
    assert latest["pairs"]["EURUSD"]["z_score_20d"] is not None
    assert latest["regime"]["usd_strength"] in {"strong", "neutral", "weak"}
    assert latest["signals"]["krw_risk_alert"] in {True, False}
    assert latest["signals"]["yen_breakout_alert"] in {True, False}
    assert metadata["pairs"]["USDKRW"]["ticker"] == "USDKRW=X"
    assert metadata["data_source"]["primary"] == "yfinance"


def test_build_exchange_payload_marks_partial_when_pairs_missing():
    prices = _sample_prices().drop(columns=["EURUSD=X"])
    latest, metadata = generate_exchange_json.build_exchange_payload(prices)

    assert latest["status"] == "partial"
    assert latest["series_valid"] is False
    assert latest["metrics_valid"] is True
    assert latest["error_code"] == "partial_pair_coverage"
    assert latest["pairs"]["EURUSD"]["value"] is None
    assert metadata["status_contract"]["status"] == "partial"


def test_write_exchange_payload_writes_source_files(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_exchange_json, "OUTPUT_DIR", tmp_path)
    latest, metadata = generate_exchange_json.build_exchange_payload(_sample_prices())

    generate_exchange_json.write_exchange_payload(latest, metadata)

    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "metadata.json").exists()
