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
import pytz
import tzlocal
from dateutil.relativedelta import relativedelta


def generate_logger(name: str, stream_level: str = None, file_level: str = None, path: Path = None):
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
        if not path.exists():
            try:
                path.mkdir(parents=True)
            except Exception as e:
                raise ValueError(f"Could not create the directory {path}. Error: {e}")

        log_file_path = path / f"{name}.log"
        file_handler = logging.FileHandler(log_file_path)
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

class CustomThread(threading.Thread):
    """
    A custom thread class that extends the functionality of the threading.Thread class.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a new instance of the class.

        Args:
            target (callable): The callable object to be invoked by the thread's run() method.
            args (tuple): The arguments to be passed to the target callable.
            daemon (bool): A flag indicating whether the thread should be a daemon thread.
            kwargs (dict): The keyword arguments to be passed to the target callable.

        Returns:
            None
        """
        self._target = kwargs.pop('target', None)
        self._args = kwargs.pop('args', ())
        self._daemon = kwargs.pop('daemon', True)
        self._kwargs = kwargs.pop('kwargs', {})
        super().__init__(target=self._target, args=self._args, daemon=self._daemon, kwargs=self._kwargs)

    @property
    def target(self):
        """
        Get the target function of the thread.
        """
        return self._target

    @property
    def args(self):
        """
        Get the arguments passed to the target function.
        """
        return self._args
    
    @property
    def daemon(self):
        """
        Get the daemon flag of the thread.
        """
        return self._daemon

    @property
    def kwargs(self):
        """
        Get the keyword arguments passed to the target function.
        """
        return self._kwargs

def pretty(command: str):
    """
    Returns a pretty version of the given command by inserting a space before each capital letter.

    Args:
        command (str): The command to make pretty.

    Returns:
        str: The pretty version of the command.
    """
    return re.sub(r'([A-Z])', r'{}\1'.format(' '), command)[1:]

def signum(x):
    """
    Returns the sign of a number.

    Parameters:
    x (float or int): The number to determine the sign of.

    Returns:
    int: 1 if x is positive, -1 if x is negative, 0 if x is zero.
    """
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0
    
def calculate_timedelta(start: datetime, end: datetime, period: str='minutes'):
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
    
    # Return the difference in the desired unit
    if period == 'minutes':
        return delta.total_seconds() / 60
    elif period == 'hours':
        return delta.total_seconds() / 3600
    elif period == 'days':
        return delta.days
    elif period == 'weeks':
        return delta.days / 7
    elif period == 'months':
        # Use relativedelta to calculate the number of months
        rd = relativedelta(end, start)
        return rd.years * 12 + rd.months
    else:
        raise ValueError("Unsupported unit. Please choose from 'minutes', 'hours', 'days', 'weeks', or 'months'.")
    
def datetime_to_unixtime(dt: datetime):
    """
    Convert a datetime object into a Unix timestamp.
    which represents the number of milliseconds since 01.01.1970, 00:00 GMT

    Practical Equivalence: For most practical purposes, GMT and UTC are nearly
    equivalent in modern usage. However, technically, UTC is more precise due
    to its incorporation of leap seconds, whereas GMT does not adjust for these.

    Naming: Despite the differences in their technical definitions, in everyday
    usage and conversation, the terms "GMT" and "UTC" are often used interchangeably.

    Args:
        dt (datetime): The datetime object to convert.

    Returns:
        float: The timestamp in milliseconds.
    """
    epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

    delta = local_to_utc(dt) - epoch

    # Convert seconds to milliseconds
    return delta.total_seconds() * 1000

def local_to_utc(dt_local):
    """
    Converts a datetime object from the local timezone to a UTC datetime object.

    Args:
        dt_local (datetime): A datetime object in the local timezone.

    Returns:
        datetime: A datetime object in UTC.
    """
    # Get the local timezone
    local_timezone = tzlocal.get_localzone()

    # Make the datetime object timezone-aware
    dt_local = dt_local.replace(tzinfo=local_timezone)

    # Convert to UTC
    dt_utc = dt_local.astimezone(pytz.utc)

    return dt_utc
