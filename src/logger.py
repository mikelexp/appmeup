from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.constants import APP_NAME


def setup_logging(verbose: bool = False) -> logging.Logger:
    log_dir = Path.home() / ".local" / "state" / "appmeup"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "appmeup.log"

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    if verbose:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)

    logger.info("%s starting (log: %s)", APP_NAME, log_file)
    return logger
