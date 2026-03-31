"""strategy 단위 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from strategy import generate_signals


def make_market(metrics_valid=True, **extra):
    payload = {
        "status": "ok" if metrics_valid else "error",
        "as_of_date": "2026-03-30" if metrics_valid else None,
        "series_valid": metrics_valid,
        "metrics_valid": metrics_valid,
        "error_code": None if metrics_valid else "constituents_fetch_failed",
        "error_message": None if metrics_valid else "missing",
    }
    payload.update(extra)
    return payload


def test_generate_signals_all_markets_valid():
    latest = {
        "date": "2026-03-31",
        "sp500": make_market(breadth_200=55, logit_z_50=0.4),
        "nikkei225": make_market(breadth_50=65, breadth_200=62, logit_z_50=0.9),
        "kospi200": make_market(breadth_50=58, breadth_200=48, logit_z_50=-0.1),
    }

    signals = generate_signals(latest)

    assert signals["partial_data"] is False
    assert all(signal["valid"] for signal in signals["signals"].values())


def test_generate_signals_invalid_when_market_missing():
    latest = {
        "date": "2026-03-31",
        "sp500": make_market(breadth_200=55, logit_z_50=0.4),
        "nikkei225": make_market(metrics_valid=False),
        "kospi200": make_market(breadth_50=58, breadth_200=48, logit_z_50=-0.1),
    }

    signals = generate_signals(latest)

    assert signals["partial_data"] is True
    for signal in signals["signals"].values():
      assert signal["valid"] is False
      assert "nikkei225" in signal["missing_markets"]
      assert signal["invalid_reason"] == "missing_market_data"
