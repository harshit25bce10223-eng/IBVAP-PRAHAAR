# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Logging Configuration
# ─────────────────────────────────────────────────────────────────────────────
import logging
import sys

LOG_LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}


def configure_logging(level: str = "INFO") -> None:
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        stream=sys.stdout,
        level=LOG_LEVELS.get(level.upper(), logging.INFO),
        format=fmt,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)