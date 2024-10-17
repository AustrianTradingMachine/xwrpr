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
import pytest


def generate_logger() -> logging.Logger:
    """
    Generate a logger with the specified name and configuration.

    Args:
        filename (str): The name of the file.

    Returns:
        logging.Logger: The configured logger instance.
    """
    
    # Create a logger with the specified name
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)

    return logger

def write_logs(caplog, filename: str) -> None:
    """
    Write records to log file.

    Args:
        caplog: The caplog fixture object.

    Returns:
        None

    Raises:
        ValueError: If the directory cannot
    """

    try:
        # Define the log file path in /tmp/xwrpr/logs
        log_file_path = Path("/tmp/xwrpr/logs") / Path(filename).name.replace('.py', '.log')
        # Ensure the logs directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    except Exception as e:
        raise ValueError(f"Could not create the directory {log_file_path}. Error: {e}")
    
    try:
        # Remove the log file if it already exists
        log_file_path.unlink()
    except FileNotFoundError as e:
        pass
    
    # Write the records to the log file
    with open(log_file_path, 'w') as log_file:
        for record in caplog.records:
            log_file.write(f"{record.levelname}: {record.message}\n")

@pytest.fixture
def demo_flag():
    # This fixture can dynamically change the value of DEMO
    return False