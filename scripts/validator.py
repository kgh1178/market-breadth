"""교차 검증: 공식 데이터 소스와 비교"""
import logging
import requests
import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

def validate_against_s5fi(computed_50d: float) -> dict:
    """
    Barchart $S5FI 또는 Investing.com과 비교.
    웹 스크래핑이 차단될 수 있으므로, 실패 시 graceful 처리.
    """
    result = {"source": "barchart_s5fi", "computed": round(computed_50d, 2),
              "official": None, "diff": None, "pass": None}
    try:
        # Investing.com은 비교적 안정적으로 접근 가능
        url = ("https://www.investing.com/indices/"
               "s-p-500-stocks-above-50-day-average")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # 페이지에서 최신 값 추출 시도
            import re
            match = re.search(
                r'data-test="instrument-price-last"[^>]*>([\d.]+)', resp.text)
            if match:
                official = float(match.group(1))
                diff = abs(computed_50d - official)
                result.update({"official": official, "diff": round(diff, 2),
                               "pass": diff < 5.0})
                return result
    except Exception as e:
        log.warning(f"S5FI validation failed: {e}")

    result["pass"] = None  # 검증 불가
    return result

def validate_against_macromicro(computed_200d: float) -> dict:
    """MacroMicro Nikkei 225 200-day breadth 스팟 체크"""
    result = {"source": "macromicro_nikkei_200d",
              "computed": round(computed_200d, 2),
              "official": None, "diff": None, "pass": None}
    try:
        # MacroMicro 공개 API (비공식)
        url = "https://en.macromicro.me/series/31801/japan-nikkei-225-200ma-breadth"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            import re
            # 페이지에서 최신 값 추출 시도
            match = re.search(r'"y":([\d.]+)', resp.text)
            if match:
                official = float(match.group(1))
                diff = abs(computed_200d - official)
                result.update({"official": official, "diff": round(diff, 2),
                               "pass": diff < 8.0})
                return result
    except Exception as e:
        log.warning(f"MacroMicro validation failed: {e}")

    result["pass"] = None
    return result

def validate_internal_consistency(breadth_50: float,
                                  breadth_200: float) -> dict:
    """내부 일관성 검증"""
    checks = {
        "range_50": 0 <= breadth_50 <= 100,
        "range_200": 0 <= breadth_200 <= 100,
    }
    checks["all_pass"] = all(checks.values())
    return checks
