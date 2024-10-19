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
from tests.helper import generate_logger, write_logs, GREEN, RESET
from pathlib import Path
import configparser
import xwrpr


# Read the configuration file
config = configparser.ConfigParser()
config_path = Path('~/.xwrpr').expanduser()/'user.ini'
config.read(config_path)

# Retrieve credentials with error handling
try:
    USERNAME = config.get('USER', 'REAL_ID')
    PASSWORD = config.get('USER', 'PASSWORD')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    raise RuntimeError(f"Configuration error: {e}")


def test_03_direct_credentials(demo_flag: bool, log_level: int, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture):
    # Create a logger with the specified name
    logger = generate_logger(log_level)

    # Set logging level to INFO to reduce the amount of captured logs
    with caplog.at_level(log_level):
        try:
            # Creating Wrapper with direct credentials
            logger.debug("Creating Wrapper with direct credentials")
            XTBData = xwrpr.Wrapper(demo = demo_flag, logger = logger, username = USERNAME, password = PASSWORD)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Getting API version
            logger.debug("Getting API version")
            version = XTBData.getVersion()

            # Check if the return value is a dict
            logger.debug("Checking if the return value is a dict")
            assert isinstance(version, dict), "Expected commission to be a dict"
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            XTBData.delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")