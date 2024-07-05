import logging
import os


def generate_logger(name: str, stream_level: str = None, file_level: str = None, path: str = None):
    """
    Generate a logger with the specified name and configuration.

    Args:
        name (str): The name of the logger.
        stream_level (str, optional): The log level for the console output. Defaults to None.
        file_level (str, optional): The log level for the file output. Defaults to None.
        path (str, optional): The path to the directory where the log file will be saved. Defaults to None.

    Returns:
        logging.Logger: The configured logger instance.
    """
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(_validate_level(stream_level, default="warning"))
    logger.addHandler(console_handler)

    if path is not None:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                raise ValueError(f"Could not create the directory {path}. Error: {e}")

        file_handler = logging.FileHandler(path + "/" + name + ".log")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(_validate_level(file_level, default="debug"))
        logger.addHandler(file_handler)

    return logger

def _validate_level(level: str = None, default: str = "debug"):
    """
    Validates the logging level and returns the corresponding logging level constant.

    Args:
        level (str, optional): The desired logging level. Defaults to None.
        default (str, optional): The default logging level. Defaults to "debug".

    Returns:
        int: The logging level constant.

    Raises:
        ValueError: If the provided level or default level is invalid.
    """
    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    if level is not None:
        if level.lower() not in levels:
            raise ValueError(f"Invalid logger level: {level}")
        level = levels[level.lower()]
    else:
        if default.lower() not in levels:
            raise ValueError(f"Invalid default level: {default}")
        level = levels[default.lower()]

    return level