"""generate_json helper 단위 테스트"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import generate_json


def _prices_frame():
    dates = pd.bdate_range("2026-01-01", periods=220)
    close = pd.DataFrame(
        {
            "AAA": range(100, 320),
            "BBB": range(200, 420),
        },
        index=dates,
    )
    adj_close = close * 0.98
    return pd.concat({"Close": close, "Adj Close": adj_close}, axis=1)


def test_structured_market_entry_keeps_required_fields():
    entry = generate_json._structured_market_entry(
        status="ok",
        as_of_date="2026-03-30",
        series_valid=True,
        metrics_valid=True,
        extra={"breadth_50": 44.0},
    )

    assert entry["status"] == "ok"
    assert entry["as_of_date"] == "2026-03-30"
    assert entry["series_valid"] is True
    assert entry["metrics_valid"] is True
    assert entry["error_code"] is None
    assert entry["error_message"] is None
    assert entry["breadth_50"] == 44.0


def test_remove_stale_series_deletes_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_json, "OUTPUT_DIR", tmp_path)
    stale_file = tmp_path / "nikkei225.json"
    stale_file.write_text("{}")

    generate_json._remove_stale_series("nikkei225")

    assert not stale_file.exists()


def test_infer_error_code_for_constituent_failures():
    assert generate_json._infer_error_code(
        RuntimeError("all constituent fetchers failed")
    ) == "constituents_fetch_failed"


def test_infer_error_code_for_price_failures():
    assert generate_json._infer_error_code(
        RuntimeError("no price data downloaded")
    ) == "prices_fetch_failed"


def test_coverage_error_message_uses_threshold():
    message = generate_json._coverage_error_message("nikkei225", 72.3)

    assert "nikkei225" in message
    assert "72.3%" in message
    assert "85.0%" in message


def test_run_marks_low_coverage_market_partial_and_removes_series(tmp_path, monkeypatch):
    stale_series = tmp_path / "sp500.json"
    stale_series.write_text("{}")

    monkeypatch.setattr(generate_json, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(generate_json, "MARKETS", {"sp500": generate_json.MARKETS["sp500"]})
    monkeypatch.setattr(generate_json, "is_any_market_open", lambda: True)
    monkeypatch.setattr(generate_json, "fetch_constituents", lambda market_id: ["AAA", "BBB"])
    monkeypatch.setattr(
        generate_json,
        "fetch_prices",
        lambda tickers, market_id: pd.concat(
            {"Close": pd.DataFrame({"AAA": [1.0, 2.0]}), "Adj Close": pd.DataFrame({"AAA": [1.0, 2.0]})},
            axis=1,
        ),
    )
    monkeypatch.setattr(
        generate_json,
        "generate_signals",
        lambda latest: {
            "date": latest["date"],
            "partial_data": True,
            "signals": {},
            "etf_map": {},
            "reference": {},
        },
    )

    generate_json.run()

    latest = json.loads((tmp_path / "latest.json").read_text())
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert latest["sp500"]["status"] == "partial"
    assert latest["sp500"]["series_valid"] is False
    assert latest["sp500"]["metrics_valid"] is False
    assert latest["sp500"]["error_code"] == "coverage_below_threshold"
    assert not stale_series.exists()
    assert metadata["markets"]["sp500"]["status"] == "partial"


def test_run_writes_structured_ok_market_with_as_of_date(tmp_path, monkeypatch):
    monkeypatch.setattr(generate_json, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(generate_json, "MARKETS", {"sp500": generate_json.MARKETS["sp500"]})
    monkeypatch.setattr(generate_json, "is_any_market_open", lambda: True)
    monkeypatch.setattr(generate_json, "fetch_constituents", lambda market_id: ["AAA", "BBB"])
    monkeypatch.setattr(generate_json, "fetch_prices", lambda tickers, market_id: _prices_frame())
    monkeypatch.setattr(
        generate_json,
        "validate_sp500_breadth",
        lambda **kwargs: {"pass_50": True},
    )
    monkeypatch.setattr(
        generate_json,
        "generate_signals",
        lambda latest: {
            "date": latest["date"],
            "partial_data": False,
            "signals": {},
            "etf_map": {},
            "reference": {},
        },
    )

    generate_json.run()

    latest = json.loads((tmp_path / "latest.json").read_text())
    series = json.loads((tmp_path / "sp500.json").read_text())
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert latest["sp500"]["status"] == "ok"
    assert latest["sp500"]["as_of_date"] is not None
    assert latest["sp500"]["series_valid"] is True
    assert latest["sp500"]["metrics_valid"] is True
    assert latest["sp500"]["price_basis"] == "split-adjusted, dividend-unadjusted"
    assert "breadth_50" in series
    assert metadata["price_column"] == "Close"
