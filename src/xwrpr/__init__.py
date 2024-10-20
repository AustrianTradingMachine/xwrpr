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

"""
xwrpr - A wrapper for the API of XTB (https://www.xtb.com)

This module provides a Wrapper class to interact with the XTB API.
"""

import sys
from importlib.metadata import version, PackageNotFoundError
from xwrpr import Wrapper
from pathlib import Path
import configparser
from typing import Optional
import logging


# Ensure the script is being run with Python 3.9 or higher
if sys.version_info < (3, 9):
    raise RuntimeError("xwrpr requires Python 3.9 or higher")

# Define the XTB Api version the xwrpr relies on
API_VERSION = '2.5.0'

# Get the version dynamically from the package metadata
try:
    __version__ = version("xwrpr")
except PackageNotFoundError:
    __version__ = "unknown"


# Read the configuration file
config = configparser.ConfigParser()
config_path = Path(__file__).parent.absolute()/'api.ini'
config.read(config_path)

MAX_CONNECTIONS = config.getint('CONNECTION', 'MAX_CONNECTIONS')
MAX_SEND_DATA = config.getint('CONNECTION', 'MAX_SEND_DATA')
MAX_RECEIVED_DATA = config.getint('CONNECTION', 'MAX_RECEIVED_DATA')
MIN_REQUEST_INTERVAL = config.getint('CONNECTION', 'MIN_REQUEST_INTERVAL')/1000
MAX_RETRIES = config.getint('CONNECTION', 'MAX_RETRIES')
MAX_REACTION_TIME = config.getint('CONNECTION', 'MAX_REACTION_TIME')/1000
MAX_QUEUE_ELEMENTS = config.getint('HANDLER', 'MAX_QUEUE_ELEMENTS')

# Alias for Wrapper to allow xwrpr() to create an instance of Wrapper
def __call__(
    demo: bool = True,

    username: Optional[str] = None,
    password: Optional[str] = None,
    path: Optional[str] = None,

    max_connections: int = MAX_CONNECTIONS,
    max_send_data: int = MAX_SEND_DATA,
    max_received_data: int = MAX_RECEIVED_DATA,
    min_request_interval: float = MIN_REQUEST_INTERVAL,
    max_retries: int = MAX_RETRIES,
    max_reaction_time: float = MAX_REACTION_TIME,
    max_queue_elements: int = MAX_QUEUE_ELEMENTS,

    logger: Optional[logging.Logger] = None,
) -> Wrapper:
    """
        Create a new instance of the Wrapper class.

        Args:
            See the Wrapper class for the arguments.

        Returns:
            Wrapper: The configured Wrapper instance.
    """

    # Create a new instance of the Wrapper class
    return Wrapper(
        demo=demo,

        username=username,
        password=password,
        path=path,

        max_connections=max_connections,
        max_send_data=max_send_data,
        max_received_data=max_received_data,
        min_request_interval=min_request_interval,
        max_retries=max_retries,
        max_reaction_time=max_reaction_time,
        max_queue_elements=max_queue_elements,

        logger=logger
    )