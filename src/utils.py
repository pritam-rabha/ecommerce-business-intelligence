import logging
import os
import sys
from pathlib import Path

# Path constants (single source of truth for file locations)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"
ASSETS_DIR = BASE_DIR / "assets"

RAW_DATA_PATH = DATA_DIR / "orders.csv"
CLEAN_DATA_PATH = DATA_DIR / "orders_clean.csv"
DATABASE_PATH = DATABASE_DIR / "ecommerce.db"

# Ensure required directories exist even on a fresh checkout
for _directory in (DATA_DIR, DATABASE_DIR, ASSETS_DIR):
    _directory.mkdir(parents=True, exist_ok=True)

# Logging
def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger instance.

    A single StreamHandler is attached the first time a logger with a given
    name is requested, preventing duplicate log lines when Streamlit
    re-executes the script on every interaction.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
        logger.propagate = False

    return logger

# Formatting helpers (used by KPI cards and chart labels)
def format_currency(value: float, symbol: str = "£") -> str:
    """Format a number as currency with thousands separators, e.g. £12,345.67."""
    try:
        return f"{symbol}{value:,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def format_number(value: float) -> str:
    """Format a number with thousands separators and no decimals."""
    try:
        return f"{value:,.0f}"
    except (TypeError, ValueError):
        return "0"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a fraction/percentage change with a leading sign, e.g. +12.3%."""
    try:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "0.0%"


def human_readable_number(value: float) -> str:
    """Compress large numbers for compact KPI display, e.g. 1.2K, 3.4M."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0"

    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"
