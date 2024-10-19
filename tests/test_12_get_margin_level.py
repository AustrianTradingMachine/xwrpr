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
from tests.helper import generate_logger, write_logs, demo_flag
import logging
import xwrpr


def test_12_get_margin_level(demo_flag, caplog):
    # Create a logger with the specified name
    logger = generate_logger()

    # Set logging level to INFO to reduce the amount of captured logs
    with caplog.at_level(logging.INFO):
        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper")
            XTBData = xwrpr.Wrapper(demo = demo_flag, logger = logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Get Margin Level
            logger.debug("Getting Margin Level")
            margin_level = XTBData.getMarginLevel()

            # Check if the return value is a dict
            logger.debug("Checking if the return value is a dict")
            assert isinstance(margin_level, dict), "Expected margin level to be a dict"

            # Log margin level
            logger.debug("Logging Margin Level")
            logger.info("Margin Level")
            details = ', '.join([f"{key}: {value}" for key, value in margin_level.items()])
            logger.info(details)
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            XTBData.delete()

    # Write records to log file
    write_logs(caplog, __file__)