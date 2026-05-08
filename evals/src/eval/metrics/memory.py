"""Peak-RSS sampler. Polls the subprocess every 100ms; reports max in MB."""

import threading
import time
from dataclasses import dataclass

import psutil


@dataclass
class MemorySampler:
    pid: int
    interval_s: float = 0.1
    peak_rss_mb: float = 0.0
    _stop: threading.Event = None  # type: ignore[assignment]
    _thread: threading.Thread = None  # type: ignore[assignment]

    def start(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        try:
            proc = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            return
        while not self._stop.is_set():
            try:
                rss_mb = proc.memory_info().rss / (1024 * 1024)
                # Include children (model loaders sometimes fork).
                for child in proc.children(recursive=True):
                    try:
                        rss_mb += child.memory_info().rss / (1024 * 1024)
                    except psutil.NoSuchProcess:
                        continue
                self.peak_rss_mb = max(self.peak_rss_mb, rss_mb)
            except psutil.NoSuchProcess:
                break
            time.sleep(self.interval_s)

    def stop(self) -> float:
        if self._stop:
            self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        return self.peak_rss_mb
