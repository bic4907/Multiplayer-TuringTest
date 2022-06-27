import threading


class InfiniteIterator(object):

    def __init__(self):
        self._lock = threading.Lock()
        self._response = None

    def __iter__(self):
        return self

    def __next__(self):
        return self._response

    def set_value(self, val):
        with self._lock:
            self._response = val

    def get_value(self):
        with self._lock:
            return self._response

    def is_null(self):
        return self._response is None
