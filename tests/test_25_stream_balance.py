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
from datetime import datetime
from dateutil.relativedelta import relativedelta


def test_25_stream_balance(
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
            # Start streaming balance
            logger.debug("Starting streaming balance")
            exchange = xtb.streamBalance()
            
            # Check if the return value is a dict
            logger.debug("Checking if the return value is a dict")
            assert isinstance(exchange, dict), "Expected a dict"

            # Log balance
            logger.info("Balance")
            stop_time = datetime.now() + relativedelta(seconds=10)
            while datetime.now() < stop_time:
                data = exchange['queue'].get()

                # Check if the return value is a dict
                logger.debug("Checking if the return value is a dict")
                assert isinstance(data, dict), "Expected a dict"
                
                # Log the data
                details = ', '.join([f"{key}: {value}" for key, value in data.items()])
                logger.info(details)
            
            # Stop the stream
            logger.debug("Stopping the stream")
            exchange['thread'].stop()
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