"""breadth_engine 단위 테스트"""
import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# scripts/ 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from breadth_engine import (
    compute_breadth, compute_deff_ci, flag_ex_dividend, compute_pwds,
)
from config import NIKKEI225, SP500

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def mock_prices_5stocks_60days():
    """5종목 × 60거래일 합성 가격 데이터"""
    np.random.seed(42)
    dates = pd.bdate_range("2025-10-01", periods=60)
    data = {}
    for i, sym in enumerate(["A", "B", "C", "D", "E"]):
        base = 100 + i * 10
        trend = np.linspace(0, 20 if i < 3 else -10, 60)
        noise = np.random.randn(60) * 2
        data[sym] = base + trend + noise
    return pd.DataFrame(data, index=dates)

# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestComputeBreadth:
    def test_basic(self, mock_prices_5stocks_60days):
        prices = mock_prices_5stocks_60days
        result = compute_breadth(prices, window=50)
        assert 0 <= result["breadth_pct"] <= 100
        assert result["n_active"] == 5
        assert 0 <= result["count_above"] <= 5

    def test_all_above(self):
        """모든 종목이 MA 위일 때 breadth = 100%"""
        dates = pd.bdate_range("2025-01-01", periods=60)
        # 지속 상승하는 가격
        prices = pd.DataFrame({
            "X": np.linspace(100, 200, 60),
            "Y": np.linspace(50, 150, 60),
        }, index=dates)
        result = compute_breadth(prices, window=50)
        assert result["breadth_pct"] == 100.0
        assert result["count_above"] == 2

    def test_insufficient_history(self):
        """히스토리 부족 종목 자동 제외"""
        dates = pd.bdate_range("2025-01-01", periods=30)
        prices = pd.DataFrame({
            "X": np.linspace(100, 130, 30),
        }, index=dates)
        result = compute_breadth(prices, window=50)
        assert result["n_active"] == 0  # 50일 미달
        assert np.isnan(result["breadth_pct"])

class TestDeffCi:
    def test_basic(self):
        ci = compute_deff_ci(k=35, n=100, icc=0.1)
        assert ci["lower"] < 35
        assert ci["upper"] > 35
        assert ci["deff"] == pytest.approx(10.9, abs=0.1)
        assert ci["n_eff"] == pytest.approx(9.17, abs=0.1)
        assert ci["confidence_grade"] == "C"

    def test_zero_icc(self):
        ci = compute_deff_ci(k=250, n=500, icc=0.0)
        assert ci["deff"] == pytest.approx(1.0)
        assert ci["n_eff"] == pytest.approx(500.0)
        assert ci["confidence_grade"] == "A"

    def test_high_icc(self):
        ci = compute_deff_ci(k=100, n=200, icc=0.5)
        assert ci["confidence_grade"] in ("B", "C")

class TestExDividend:
    def test_japan_march(self):
        assert flag_ex_dividend("2026-03-30", NIKKEI225) is True

    def test_japan_july(self):
        assert flag_ex_dividend("2026-07-15", NIKKEI225) is False

    def test_sp500_non_quarter(self):
        assert flag_ex_dividend("2026-02-15", SP500) is False

class TestPwds:
    def test_equal_prices(self, mock_prices_5stocks_60days):
        """PWDS는 실수 값 반환"""
        pwds = compute_pwds(mock_prices_5stocks_60days, window=50)
        assert isinstance(pwds, float)
