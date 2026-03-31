"""
Breadth Engine 단위 테스트
==========================
v3.1  2026-03-31  Fix: auto_adjust=False 형식 테스트 데이터
"""

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from breadth_engine import (
    compute_breadth,
    compute_breadth_timeseries,
    compute_deff_ci,
    compute_pwds,
    flag_ex_dividend_window,
)


@pytest.fixture
def sample_prices_auto_adjust_false():
    dates = pd.bdate_range("2025-06-01", periods=60)
    tickers = ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE"]

    close_data = {
        "AAAA": np.linspace(100, 120, 60),
        "BBBB": np.linspace(100, 80, 60),
        "CCCC": np.concatenate([np.full(30, 50), np.linspace(50, 70, 30)]),
        "DDDD": np.concatenate([np.full(30, 50), np.linspace(50, 35, 30)]),
        "EEEE": np.concatenate([np.full(20, np.nan), np.linspace(60, 65, 40)]),
    }
    adj_close_data = {k: v * 0.97 for k, v in close_data.items()}

    arrays = {
        "Close": pd.DataFrame(close_data, index=dates),
        "Adj Close": pd.DataFrame(adj_close_data, index=dates),
        "Volume": pd.DataFrame(
            {t: np.random.randint(1e6, 1e7, 60) for t in tickers},
            index=dates,
        ),
    }
    return pd.concat(arrays, axis=1)


@pytest.fixture
def sample_prices_full_data():
    dates = pd.bdate_range("2025-06-01", periods=60)

    close_data = {
        "AA": np.linspace(100, 120, 60),
        "BB": np.linspace(100, 80, 60),
        "CC": np.full(60, 100.0),
        "DD": np.linspace(100, 110, 60),
        "EE": np.linspace(100, 85, 60),
    }
    adj_close_data = {k: v * 0.96 for k, v in close_data.items()}

    arrays = {
        "Close": pd.DataFrame(close_data, index=dates),
        "Adj Close": pd.DataFrame(adj_close_data, index=dates),
    }
    return pd.concat(arrays, axis=1)


class TestComputeBreadth:
    def test_basic_calculation(self, sample_prices_auto_adjust_false):
        result = compute_breadth(sample_prices_auto_adjust_false, window=50)

        assert result["breadth"] is not None
        assert 0 <= result["breadth"] <= 100
        assert result["n_above"] + (result["n_valid"] - result["n_above"]) == result["n_valid"]

    def test_n_valid_excludes_insufficient_data(self, sample_prices_auto_adjust_false):
        result = compute_breadth(sample_prices_auto_adjust_false, window=50)

        assert result["n_valid"] == 4
        assert result["n_excluded"] == 1
        assert result["n_total"] == 5

    def test_above_below_classification(self, sample_prices_auto_adjust_false):
        result = compute_breadth(sample_prices_auto_adjust_false, window=50)

        assert result["per_stock"]["AAAA"]["above"] is True
        assert result["per_stock"]["BBBB"]["above"] is False

    def test_min_periods_enforced(self, sample_prices_auto_adjust_false):
        result = compute_breadth(sample_prices_auto_adjust_false, window=50)
        assert "EEEE" not in result["per_stock"]

    def test_all_valid_when_full_data(self, sample_prices_full_data):
        result = compute_breadth(sample_prices_full_data, window=50)
        assert result["n_valid"] == result["n_total"]
        assert result["n_excluded"] == 0


class TestDividendInvariance:
    def test_breadth_uses_close_not_adj_close(self, sample_prices_auto_adjust_false):
        system_result = compute_breadth(sample_prices_auto_adjust_false, window=50)

        close = sample_prices_auto_adjust_false["Close"]
        close_sma = close.rolling(50, min_periods=50).mean()
        close_latest = close.iloc[-1]
        close_sma_latest = close_sma.iloc[-1]
        close_valid = close_latest.notna() & close_sma_latest.notna()
        close_above = ((close_latest > close_sma_latest) & close_valid).sum()
        close_breadth = close_above / close_valid.sum() * 100

        assert abs(system_result["breadth"] - close_breadth) < 0.01


class TestDeffCI:
    def test_ci_contains_point_estimate(self):
        ci = compute_deff_ci(n_above=100, n_valid=500, icc=0.08)
        p_hat = 100 / 500 * 100
        assert ci["lower"] is not None
        assert ci["upper"] is not None
        assert ci["lower"] <= p_hat <= ci["upper"]

    def test_higher_icc_wider_ci(self):
        ci_low = compute_deff_ci(n_above=100, n_valid=500, icc=0.05)
        ci_high = compute_deff_ci(n_above=100, n_valid=500, icc=0.15)
        width_low = ci_low["upper"] - ci_low["lower"]
        width_high = ci_high["upper"] - ci_high["lower"]
        assert width_high > width_low

    def test_zero_n_valid(self):
        ci = compute_deff_ci(n_above=0, n_valid=0, icc=0.08)
        assert ci["lower"] is None
        assert ci["upper"] is None


class TestExDividendFlag:
    def test_flags_within_window(self):
        ex_dates = {
            "AAPL": ["2025-08-14"],
            "MSFT": ["2025-08-20"],
        }
        ref = pd.Timestamp("2025-08-14")
        result = flag_ex_dividend_window(ex_dates, ref, buffer_days=1)
        assert result["count"] == 1
        assert "AAPL" in result["tickers"]
        assert "MSFT" not in result["tickers"]


class TestTimeseries:
    def test_timeseries_length(self, sample_prices_full_data):
        ts = compute_breadth_timeseries(sample_prices_full_data, window=50, lookback=20)
        assert len(ts) > 0
        assert "breadth" in ts.columns
        assert "n_valid" in ts.columns
