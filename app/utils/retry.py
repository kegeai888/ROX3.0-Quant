"""Simple retry helper for flaky network (e.g. East Money)."""
import time


def run_with_retry(func, max_attempts=3, delays=(1, 2, 3)):
    """Run func() with retries on connection-like errors. delays in seconds."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exc = e
            err_str = str(e).lower()
            if "remote disconnected" in err_str or "connection aborted" in err_str or "connection" in err_str:
                if attempt < max_attempts - 1 and attempt < len(delays):
                    time.sleep(delays[attempt])
                    continue
            raise
    raise last_exc
