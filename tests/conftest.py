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

import pytest
import logging

def _set_logger_level(level: str) -> int:
    """
    Set the logging level for the logger.

    Args:
        level (str): The logging level.

    Returns:
        int: The logging level as an integer.

    Raises:
        ValueError: If the logging level is invalid.
    """

    # Define the mapping of logging levels
    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    if level is None:
        level = 'DEBUG'

    level = level.lower()

    if level not in levels:
        raise ValueError(f"Invalid logger level: {level}")

    return levels[level]

def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add custom command-line options for pytest.

    Args:
        parser: The parser object to add options to.

    Returns:
        None
    """

    parser.addoption(
        "--demo", action = "store_true", default = False, help = "Run tests in demo mode"
    )

@pytest.fixture
def demo_flag(request):
    """
    Fixture to dynamically change the value of DEMO based on the command-line option.

    Args:
        request (pytest.FixtureRequest): The fixture request object.

    Returns:
        bool: The value of the --demo command-line option.
    """

    return request.config.getoption("--demo")

@pytest.fixture
def log_level(request):
    """
    Fixture to dynamically change the logging level based on the command-line option.

    Args:
        request (pytest.FixtureRequest): The fixture request object.

    Returns:
        int: The logging level as an integer.
    """

    return _set_logger_level(request.config.getoption("--log-level"))