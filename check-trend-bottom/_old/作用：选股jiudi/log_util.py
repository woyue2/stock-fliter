# -*- coding: utf-8 -*-
"""Simple stdout/stderr tee to a log file."""
from __future__ import annotations

import atexit
import sys
from pathlib import Path


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def setup_run_log(script_path: Path) -> Path:
    """Mirror stdout/stderr to '<script>.log' and return the log path."""
    log_path = script_path.with_suffix(".log")
    log_file = log_path.open("a", encoding="utf-8")

    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)

    atexit.register(log_file.close)
    return log_path
