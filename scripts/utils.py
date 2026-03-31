"""유틸리티: 거래일 체크, 로깅, 재시도"""

import functools
import logging
import time
from datetime import date

import exchange_calendars as xcals
import pandas as pd

from config import MARKETS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def is_any_market_open(d: date = None) -> bool:
    """적어도 하나의 시장이 오늘 거래일인지 확인"""
    d = d or date.today()
    ts = pd.Timestamp(d)
    for cfg in MARKETS.values():
        cal = xcals.get_calendar(cfg.exchange_cal)
        if cal.is_session(ts):
            return True
    return False


def retry_with_backoff(max_retries=3, initial_wait=5.0):
    """지수적 백오프 재시도 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = initial_wait
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_retries:
                        log.error("%s failed after %s retries: %s", func.__name__, max_retries, exc)
                        raise
                    log.warning("%s attempt %s failed: %s, retrying in %ss", func.__name__, attempt + 1, exc, wait)
                    time.sleep(wait)
                    wait *= 2
        return wrapper
    return decorator
