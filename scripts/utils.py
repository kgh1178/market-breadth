"""유틸리티: 거래일 체크, 로깅, 재시도"""
import exchange_calendars as xcals
import pandas as pd
from datetime import date
from config import MARKETS
import time, functools, logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def is_any_market_open(d: date = None) -> bool:
    """적어도 하나의 시장이 오늘 거래일인지 확인"""
    d = d or date.today()
    ts = pd.Timestamp(d)
    for cfg in MARKETS.values():
        cal = xcals.get_calendar(cfg.exchange_cal_code)
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
                except Exception as e:
                    if attempt == max_retries:
                        log.error(f"{func.__name__} failed after "
                                  f"{max_retries} retries: {e}")
                        raise
                    log.warning(f"{func.__name__} attempt {attempt+1} "
                                f"failed: {e}, retrying in {wait}s")
                    time.sleep(wait)
                    wait *= 2
        return wrapper
    return decorator
