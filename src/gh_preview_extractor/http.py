from __future__ import annotations

import threading
import requests

_thread_local = threading.local()


def get_session() -> requests.Session:
    """
    requests.Session isn't guaranteed to be thread-safe, so we keep one per thread.
    """
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        _thread_local.session = sess
    return sess
