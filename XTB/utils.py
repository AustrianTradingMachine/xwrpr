import logging
import os



def generate_logger(stream_level: str = None, file_level: str = None, name: str = None, path: str = None):
    """
    Sets up and returns a logger object with the specified configurations.

    Args:
        stream_level (str, optional): The log level for the console output. Defaults to None.
        file_level (str, optional): The log level for the file output. Defaults to None.
        name (str, optional): The name of the logger. Required.
        path (str, optional): The path to the directory where the log file will be saved. Defaults to None.

    Returns:
        logger (logging.Logger): The configured logger object.

    Raises:
        ValueError: If the name argument is not provided.
        ValueError: If the specified directory path cannot be created.
    """
    if name is None:
        raise ValueError("Please provide a name for the logger.")

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
    Validates the log level.

    Args:
        level (str, optional): The log level to validate. Defaults to None.
        default (str, optional): The default log level. Defaults to "debug".

    Raises:
        ValueError: If the provided log level is invalid.

    Returns:
        int: The validated log level.
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
            raise ValueError(f"Invalid log level: {level}")
        level = levels[level.lower()]
    else:
        level = levels[default.lower()]

    return level