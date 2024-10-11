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
import threading
import re
import datetime
import tzlocal
from typing import Optional
from dateutil.relativedelta import relativedelta


def generate_logger(
    name: str,
    stream_level: Optional[str] = None,
    file_level: Optional[str] = None,
    path: Optional[Path] = None
) -> logging.Logger:
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

    # Create a logger with the specified name
    logger = logging.getLogger(name)
    # Define the log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the logger level to DEBUG
    logger.setLevel(logging.DEBUG)

    # Create a stream handler for the console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(_validate_level(stream_level, default="warning"))
    logger.addHandler(stream_handler)

    if path is not None:
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except Exception as e:
                raise ValueError(f"Could not create the directory {path}. Error: {e}")

        # Create a file handler for the log file
        log_file_path = path / f"{name}.log"
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(_validate_level(file_level, default="debug"))
        logger.addHandler(file_handler)

    return logger

def _validate_level(
    level: Optional[str] = None,
    default: str = "debug"
    ) -> int:
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

    # Define the mapping of logging levels
    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    # Set the logging level
    if level is not None:
        if level.lower() not in levels:
            raise ValueError(f"Invalid logger level: {level}")
        level = levels[level.lower()]
    else:
        if default.lower() not in levels:
            raise ValueError(f"Invalid default level: {default}")
        level = levels[default.lower()]

    return level

class CustomThread(threading.Thread):
    """
    A custom thread class that extends the functionality of the threading.Thread class.

    Attributes:
        target (callable): The callable object to be invoked by the thread's run() method.
        args (tuple): The arguments to be passed to the target callable.
        daemon (bool): A flag indicating whether the thread should be a daemon thread.
        kwargs (dict): The keyword arguments to be passed to the target callable.

    Methods:
        None

    Properties:
        target (callable): The callable object to be invoked by the thread's run() method.
        args (tuple): The arguments to be passed to the target callable.
        daemon (bool): A flag indicating whether the thread should be a daemon thread.
        kwargs (dict): The keyword arguments to be passed to the target callable.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize a new instance of the class.

        Args:
            args: The positional arguments to be passed to the threading.Thread class.
            kwargs: The keyword arguments to be passed to the threading.Thread class.

        Returns:
            None
        """

        # Extract the custom attributes
        self._target = kwargs.pop('target', None)
        self._args = kwargs.pop('args', ())
        self._daemon = kwargs.pop('daemon', True)
        self._kwargs = kwargs.pop('kwargs', {})

        # Create a new instance of the threading.Thread class
        super().__init__(
            target=self._target,
            args=self._args,
            daemon=self._daemon,
            kwargs=self._kwargs
        )

    @property
    def target(self):
        return self._target

    @property
    def args(self):
        return self._args
    
    @property
    def daemon(self):
        return self._daemon

    @property
    def kwargs(self):
        return self._kwargs

def pretty(command: str) -> str:
    """
    Returns a pretty version of the given command by inserting a space before each capital letter.

    Args:
        command (str): The command to make pretty.

    Returns:
        str: The pretty version of the command.
    """

    return re.sub(r'([A-Z])', r'{}\1'.format(' '), command)[1:]

def calculate_timedelta(start: datetime, end: datetime, period: str = 'minutes') -> float:
    """
    Calculate the time difference between two datetime objects.

    Parameters:
        start (datetime): The starting datetime object.
        end (datetime): The ending datetime object.
        period (str, optional): The unit of time to calculate the difference in. Defaults to 'minutes'.

    Returns:
        float: The difference between the two datetime objects in the specified unit.

    Raises:
        ValueError: If an unsupported unit is provided.

    Supported units:
        - 'minutes'
        - 'hours'
        - 'days'
        - 'weeks'
        - 'months'
    """
    
    # Calculate the difference
    delta = end - start

    # Supported units and conversion factors (for seconds-based units)
    conversions = {
        'minutes': delta.total_seconds() / 60,
        'hours': delta.total_seconds() / 3600,
        'days': delta.days,
        'weeks': delta.days / 7,
        'months': relativedelta(end, start).years * 12 + relativedelta(end, start).months
    }

    # Return the converted value or raise an error if the period is not supported
    try:
        return conversions[period]
    except KeyError:
        raise ValueError(f"Unsupported unit '{period}'. Please choose from 'minutes', 'hours', 'days', 'weeks', or 'months'.")

def datetime_to_unixtime(dt: datetime.datetime) -> float:
    """
    Convert a datetime object into a Unix timestamp (milliseconds since 01.01.1970, 00:00 UTC).
    
    Args:
        dt (datetime): The datetime object to convert.
    
    Returns:
        float: The timestamp in milliseconds.
    """

    # Ensure the datetime is in UTC
    dt_utc = dt.astimezone(datetime.timezone.utc)

    # Get the Unix timestamp in seconds and convert to milliseconds
    return dt_utc.timestamp() * 1000

def local_to_utc(dt_local: datetime.datetime) -> datetime.datetime:
    """
    Converts a datetime object from the local timezone to UTC.

    Args:
        dt_local (datetime): A datetime object in the local timezone.

    Returns:
        datetime: A datetime object in UTC.
    """

    # Get the local timezone
    local_timezone = tzlocal.get_localzone()

    # Convert the naive datetime to the local timezone, if necessary
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=local_timezone)
    
    # Convert to UTC
    return dt_local.astimezone(datetime.timezone.utc)