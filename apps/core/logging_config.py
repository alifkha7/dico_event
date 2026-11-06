import sys
from pathlib import Path

from loguru import logger

_logging_initialized = False


def setup_logging(base_dir=None):
    global _logging_initialized
    if _logging_initialized:
        return logger

    if base_dir is None:
        base_dir = Path.cwd()
    else:
        base_dir = Path(base_dir)

    log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}"

    # Remove default handler
    logger.remove()

    # Console sink (optional, for debugging)
    logger.add(sys.stdout, format=log_format, level="INFO")

    use_enqueue = sys.platform != "win32"

    # application.log (INFO and above)
    app_log_path = base_dir / "application.log"
    logger.add(
        str(app_log_path),
        format=log_format,
        level="INFO",
        rotation="1 day",
        enqueue=use_enqueue,
        delay=True,
    )

    # error.log (ERROR and above)
    error_log_path = base_dir / "error.log"
    logger.add(
        str(error_log_path),
        format=log_format,
        level="ERROR",
        rotation="1 day",
        enqueue=use_enqueue,
        delay=True,
    )

    _logging_initialized = True
    return logger
