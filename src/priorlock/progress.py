"""Live progress reporting.

Long-running steps must say what they are doing *while* they do it. A tool that
prints nothing for ninety seconds is indistinguishable from a hung one, and the
first thing a user does about that is kill it.

Two output modes, chosen automatically:

**TTY** — an in-place spinner with elapsed time, rewritten on the same line and
replaced by the final result. Compact.

**Pipe / log file** — no cursor tricks (they render as line noise in a log).
Instead: a "start" line immediately, a heartbeat every ``HEARTBEAT_SEC`` while
the step runs, and a result line with elapsed time. Verbose but greppable, and
it still proves the process is alive.
"""
from __future__ import annotations

import itertools
import os
import sys
import threading
import time
from contextlib import contextmanager

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
HEARTBEAT_SEC = 10.0
SLOW_SEC = 2.0          # below this, don't bother announcing a start line


def is_tty(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("PRIORLOCK_NO_SPINNER"):
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


def supports_colour(stream=None) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return True


def fmt_elapsed(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


class Step:
    """One named unit of work with a live status line.

    ::

        with Step("G1 gold score") as s:
            score = expensive()
            s.done(True, f"gap_score={score}")
    """

    def __init__(self, label: str, width: int = 34, stream=None):
        self.label = label
        self.width = width
        self.stream = stream or sys.stdout
        self.tty = is_tty(self.stream)
        self.start = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._finished = False

    # ── lifecycle ────────────────────────────────────────────────────────────

    def __enter__(self) -> "Step":
        self.start = time.monotonic()
        if self.tty:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            self._thread = threading.Thread(target=self._heartbeat, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self._finished:
            self.done(exc_type is None, "" if exc_type is None else str(exc))
        return False

    # ── output ───────────────────────────────────────────────────────────────

    def _spin(self) -> None:
        for frame in itertools.cycle(FRAMES):
            if self._stop.wait(0.08):
                return
            elapsed = time.monotonic() - self.start
            line = (f"\r{DIM}{frame}{RESET} {self.label.ljust(self.width)} "
                    f"{DIM}{fmt_elapsed(elapsed)}{RESET}   ")
            self.stream.write(line)
            self.stream.flush()

    def _heartbeat(self) -> None:
        announced = False
        while not self._stop.wait(0.25):
            elapsed = time.monotonic() - self.start
            if not announced and elapsed >= SLOW_SEC:
                self.stream.write(f"   {DIM}· {self.label} …{RESET}\n")
                self.stream.flush()
                announced = True
            if announced and elapsed >= HEARTBEAT_SEC and \
                    int(elapsed) % int(HEARTBEAT_SEC) == 0:
                self.stream.write(
                    f"   {DIM}· still running — {fmt_elapsed(elapsed)}{RESET}\n")
                self.stream.flush()
                self._stop.wait(1.1)     # avoid printing the same second twice

    def done(self, ok: bool, detail: str = "", *, warn: bool = False) -> None:
        self._finished = True
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.5)
        elapsed = time.monotonic() - self.start

        if warn:
            mark = f"{YELLOW}WARN{RESET}"
        elif ok:
            mark = f"{GREEN}PASS{RESET}"
        else:
            mark = f"{RED}FAIL{RESET}"

        if self.tty:
            self.stream.write("\r\033[K")
        self.stream.write(
            f"{self.label.ljust(self.width)} {mark}  "
            f"{DIM}{fmt_elapsed(elapsed).rjust(6)}{RESET}  {DIM}{detail}{RESET}\n"
        )
        self.stream.flush()

    def note(self, text: str) -> None:
        """Emit a sub-line without ending the step."""
        if self.tty:
            self.stream.write("\r\033[K")
        self.stream.write(f"   {DIM}{text}{RESET}\n")
        self.stream.flush()


@contextmanager
def phase(title: str, index: int | None = None, total: int | None = None,
          stream=None):
    """A titled block with a total elapsed time on exit."""
    stream = stream or sys.stdout
    tag = f"[{index}/{total}] " if index and total else ""
    stream.write(f"\n{BOLD}{tag}{title}{RESET}\n")
    stream.flush()
    start = time.monotonic()
    try:
        yield
    finally:
        stream.write(f"{DIM}   ⤷ {fmt_elapsed(time.monotonic() - start)}{RESET}\n")
        stream.flush()


def line(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    stream.write(f"{DIM}{text}{RESET}\n")
    stream.flush()
