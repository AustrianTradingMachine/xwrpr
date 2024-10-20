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


def test_22_get_trade_records(
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
            # Get trades history
            logger.debug("Getting trades history")
            trades_history = xtb.getTradesHistory(start = datetime.now()-timedelta(weeks = 52), end = datetime.now())

            orders = []
            for records in trades_history:
                orders.append(records['position'])

            # Get trades history
            logger.debug("Getting trades records")
            trades_records = xtb.getTradeRecords(orders = orders)

            # Check if the return value is a list
            logger.debug("Checking if the return value is a list")
            assert isinstance(trades_records, list), "Expected trades history to be a list"

            # Log trades history
            logger.debug("Logging trades history")
            for records in trades_records:
                logger.info("Position: %s", records['position'])
                details = ', '.join([f"{key}: {value}" for key, value in records.items()])
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