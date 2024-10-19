#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    xwrpr - A wrapper for the API of XTB (https://www.xtb.com)
#
#    Copyright (C) 2024  Philipp Craighero
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###########################################################################

import logging
from pathlib import Path

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"

def generate_logger(log_level: int = logging.INFO) -> logging.Logger:
    """
    Generate a logger with the specified name and configuration.

    Args:
        log_level (int, optional): The log level for the console output. Defaults to logging.INFO.

    Returns:
        logging.Logger: The configured logger instance.
    """
    
    # Create a logger with the specified name
    logger = logging.getLogger()
    logger.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)

    return logger

def write_logs(caplog, filename: str) -> str:
    """
    Write records to log file.

    Args:
        caplog: The caplog fixture object.
        filename (str): The name of the file to write the logs to.

    Returns:
        str: The path to the log file

    Raises:
        ValueError: If the directory cannot
    """

    try:
        # Define the log file path in /tmp/xwrpr/logs
        log_file_path = Path("/tmp/xwrpr/logs") / Path(filename).name.replace('.py', '.log')
        # Ensure the logs directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        # If the directory already exists, pass
        pass
    except Exception as e:
        raise ValueError(f"Could not create the directory {log_file_path}. Error: {e}")
    
    try:
        # Remove the log file if it already exists
        log_file_path.unlink()
    except FileNotFoundError as e:
        # If the file does not exist, pass
        pass
    
    # Write the records to the log file
    with open(log_file_path, 'w') as log_file:
        for record in caplog.records:
            log_file.write(f"{record.levelname}: {record.message}\n")

    return log_file_path