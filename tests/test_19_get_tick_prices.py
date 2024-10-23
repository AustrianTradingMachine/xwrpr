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
import xwrpr
from datetime import datetime, timedelta


def test_19_get_tick_prices(
    demo_flag: bool,
    log_level: int,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture
) -> None:
    # Create a logger with the specified name
    logger = generate_logger(log_level)

    # Capture the logs
    with caplog.at_level(log_level):
        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper")
            xtb = xwrpr.Wrapper(demo = demo_flag, logger = logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Check failure
            logger.debug("Checking failure conditions: level < -1")
            with pytest.raises(ValueError):
                tick_prices = xtb.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()+timedelta(seconds = 3), level = -2)
            logger.debug("Checking failure conditions: timestamp < current time")
            with pytest.raises(ValueError):
                tick_prices = xtb.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()-timedelta(seconds = 3), level = -1)

            # Get tick prices
            logger.debug("Getting tick prices")
            tick_prices = xtb.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()+timedelta(seconds = 3), level = 1)

            # Check if the return value is a dictionary
            logger.debug("Checking if the return value is a dictionary")
            assert isinstance(tick_prices, dict), "Expected tick prices to be a dictionary"
            logger.debug("Checking if quotations is a list")
            assert isinstance(tick_prices["quotations"], list), "Expected quotations to be a list"

            # Log tick prices
            logger.debug("Logging each tick price")
            for record in tick_prices["quotations"]:
                logger.info("Symbol: %s", record['symbol'])
                details = ', '.join([f"{key}: {value}" for key, value in record.items()])
                logger.info(details)
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            xtb._delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")
                
    # Clear the captured logs
    caplog.clear()