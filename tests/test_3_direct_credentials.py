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
from helper.helper import generate_logger, write_logs, demo_flag
import logging
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


def test_3_direct_credentials(demo_flag, caplog):
    # Create a logger with the specified name
    logger = generate_logger()

    with caplog.at_level(logging.WARNING):
        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper with direct credentials")
            XTBData=xwrpr.Wrapper(demo=demo_flag, logger=logger, username=USERNAME, password=PASSWORD)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # getting API version
            logger.debug("Getting API version")
            version=XTBData.getVersion()

            # Check if the return value is a dict
            logger.debug("Checking if the return value is a dict")
            assert isinstance(version, dict), "Expected commission to be a dict"
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            XTBData.delete()

    # Write records to log file
    write_logs(caplog, __file__)