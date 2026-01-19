# app/core/logging.py
"""
Sistema de logging melhorado para o Genesys Stock Manager.

Features:
- Cores para níveis de log (console)
- Formato mais legível com separadores visuais
- Request ID tracking
- Timing helpers para debugging
"""

import logging
import os
import re
import sys
import time
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from collections.abc import Callable

# -------- request-id ----------
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


# -------- ANSI Colors ----------
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


# Level -> (color, short_name)
LEVEL_STYLES = {
    logging.DEBUG: (Colors.CYAN, "DBG"),
    logging.INFO: (Colors.GREEN, "INF"),
    logging.WARNING: (Colors.YELLOW, "WRN"),
    logging.ERROR: (Colors.RED, "ERR"),
    logging.CRITICAL: (Colors.BRIGHT_RED + Colors.BOLD, "CRT"),
}


class RequestIdFilter(logging.Filter):
    """Adds request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = _request_id_ctx.get()
        record.request_id = rid or "-"
        return True


class ColoredFormatter(logging.Formatter):
    """
    Formatter with colors for console output.

    Format: HH:MM:SS.mmm | LEVEL | logger.name | [rid] | message
    """

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and _supports_color()

    def format(self, record: logging.LogRecord) -> str:
        # Time (only HH:MM:SS.mmm for readability)
        dt = datetime.fromtimestamp(record.created)
        time_str = dt.strftime("%H:%M:%S") + f".{int(record.msecs):03d}"

        # Level with color
        color, short_level = LEVEL_STYLES.get(record.levelno, (Colors.WHITE, record.levelname[:3]))

        # Logger name - shorten for readability
        name = record.name
        # Remove common prefixes
        for prefix in ("app.", "gsm."):
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        # Further shorten common paths
        name = name.replace(".usecases.", ".").replace(".services.", ".")
        name = name.replace("domains.", "").replace("api.v1.", "api.")

        # Request ID
        rid = getattr(record, "request_id", "-")

        # Build the formatted message
        if self.use_colors:
            parts = [
                f"{Colors.DIM}{time_str}{Colors.RESET}",
                f"{color}{short_level:>3}{Colors.RESET}",
                f"{Colors.BRIGHT_BLUE}{name:<25}{Colors.RESET}",
                f"{Colors.DIM}[{rid}]{Colors.RESET}",
                record.getMessage(),
            ]
        else:
            parts = [
                time_str,
                f"{short_level:>3}",
                f"{name:<25}",
                f"[{rid}]",
                record.getMessage(),
            ]

        formatted = " | ".join(parts)

        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class FileFormatter(logging.Formatter):
    """
    Clean formatter for file output (no colors).

    Format: YYYY-MM-DD HH:MM:SS.mmm | LEVEL | logger | [rid] | message
    """

    def format(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S") + f".{int(record.msecs):03d}"

        name = record.name
        for prefix in ("app.", "gsm."):
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break
        name = name.replace(".usecases.", ".").replace(".services.", ".")
        name = name.replace("domains.", "").replace("api.v1.", "api.")

        rid = getattr(record, "request_id", "-")
        level = record.levelname[:3]

        formatted = f"{time_str} | {level:>3} | {name:<25} | [{rid}] | {record.getMessage()}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def _supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    # Windows 10+ supports colors, but needs to be enabled
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences on Windows
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    # Unix-like systems usually support colors
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# -------- Request ID helpers ----------
def get_request_id() -> str | None:
    """Returns current request id (or None if not set)."""
    return _request_id_ctx.get()


def get_request_id_or(default: str = "-") -> str:
    rid = _request_id_ctx.get()
    return rid if rid else default


def set_request_id(rid: str | None) -> None:
    _request_id_ctx.set(rid)


# -------- Log rotation helpers ----------
_DATE_SUFFIX = "%Y-%m-%d"
_LOG_RE = re.compile(r"^(?P<base>.+)\.log\.(?P<date>\d{4}-\d{2}-\d{2})$")


def _purge_old_logs(log_dir: str, base_name: str, days: int = 30) -> int:
    """Delete log files older than N days."""
    cutoff = (datetime.now() - timedelta(days=days)).date()
    removed = 0
    for fname in os.listdir(log_dir):
        m = _LOG_RE.match(fname)
        if not m:
            continue
        if not m.group("base").endswith(base_name):
            continue
        try:
            dt = datetime.strptime(m.group("date"), _DATE_SUFFIX).date()
        except ValueError:
            continue
        if dt < cutoff:
            try:
                os.remove(os.path.join(log_dir, fname))
                removed += 1
            except OSError:
                pass
    return removed


# -------- Timing helpers ----------
@contextmanager
def log_timing(operation: str, logger: logging.Logger | str | None = None, **context):
    """
    Context manager that logs operation duration.

    Usage:
        with log_timing("import_product", product_id=123):
            # do work

    Logs:
        -> import_product starting (product_id=123)
        <- import_product done in 150.2ms (product_id=123)
    """
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    elif logger is None:
        logger = logging.getLogger("gsm.timing")

    ctx_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
    ctx_display = f" ({ctx_str})" if ctx_str else ""

    logger.debug("-> %s starting%s", operation, ctx_display)
    t0 = time.perf_counter()

    try:
        yield
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.info("<- %s done in %.1fms%s", operation, duration_ms, ctx_display)
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.error("<- %s FAILED in %.1fms: %s%s", operation, duration_ms, e, ctx_display)
        raise


def log_timed(logger: logging.Logger | str | None = None):
    """
    Decorator that logs function execution time.

    Usage:
        @log_timed("gsm.mymodule")
        def my_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with log_timing(func.__name__, logger):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def log_progress(
    current: int,
    total: int,
    operation: str,
    logger: logging.Logger | str | None = None,
    every_n: int = 10,
):
    """
    Log progress for batch operations.

    Usage:
        for i, item in enumerate(items):
            log_progress(i + 1, len(items), "processing", every_n=50)
    """
    if current % every_n == 0 or current == total:
        if isinstance(logger, str):
            logger = logging.getLogger(logger)
        elif logger is None:
            logger = logging.getLogger("gsm.progress")

        pct = (current / total * 100) if total > 0 else 0
        logger.info("[%d/%d] %.0f%% - %s", current, total, pct, operation)


# -------- Main setup ----------
def setup_logging() -> None:
    """Configure logging for the application."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = os.getenv("LOG_DIR", os.path.join(os.getcwd(), "logs"))
    base_name = os.getenv("LOG_BASENAME", "gsm")
    retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    use_colors = os.getenv("LOG_COLORS", "true").lower() in ("true", "1", "yes")

    os.makedirs(log_dir, exist_ok=True)
    logfile = os.path.join(log_dir, f"{base_name}.log")

    # Console handler (with colors)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ColoredFormatter(use_colors=use_colors))
    console.addFilter(RequestIdFilter())

    # File handler (no colors, full date)
    fileh = TimedRotatingFileHandler(
        filename=logfile,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
        delay=True,
        utc=False,
    )
    fileh.suffix = _DATE_SUFFIX
    fileh.setFormatter(FileFormatter())
    fileh.addFilter(RequestIdFilter())

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(fileh)

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(os.getenv("HTTPX_LOG_LEVEL", "WARNING").upper())
    logging.getLogger("httpcore").setLevel(os.getenv("HTTPX_LOG_LEVEL", "WARNING").upper())
    logging.getLogger("urllib3").setLevel(os.getenv("URLLIB3_LOG_LEVEL", "WARNING").upper())
    logging.getLogger("apscheduler").setLevel(os.getenv("APSCHED_LOG_LEVEL", "WARNING").upper())

    # Purge old logs
    removed = _purge_old_logs(log_dir, base_name, days=retention_days)
    if removed:
        logging.getLogger("gsm.logging").info("Purged %d old log file(s)", removed)

    logging.getLogger("gsm.logging").debug(
        "Logging initialized: level=%s, colors=%s", level, use_colors
    )
