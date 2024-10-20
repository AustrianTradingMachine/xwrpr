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
from tests.helper import generate_logger, write_logs, GREEN, YELLOW, RESET
import xwrpr
from datetime import datetime, timedelta


def test_24_trade_transaction(
    demo_flag: bool,
    log_level: int,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture,
    trade_flag: bool
) -> None:

    if not demo_flag:
        with capsys.disabled():
            print(f"\n{YELLOW}Skipping test as it requires a demo account{RESET}")
            print (f"\n{YELLOW}Run the test with \"pytest --demo\" flag to execute the test{RESET}")
            print (f"\n{YELLOW}Make sure your demo account is still active{RESET}\n")
        pytest.skip(reason = "Skipping test as it requires a demo account")

    if not trade_flag:
        with capsys.disabled():
            print(f"\n{YELLOW}Skipping test as it requires your agreement for a trade{RESET}")
            print (f"\n{YELLOW}Run the test with \"pytest --trade\" flag if you agree to make this trade{RESET}")
        pytest.skip(reason = "Skipping test as it requires your agreement for a trade")

    # Create a logger with the specified name
    logger = generate_logger(log_level)

    # Set logging level to INFO to reduce the amount of captured logs
    with caplog.at_level(log_level):
        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper")
            XTBData = xwrpr.Wrapper(demo = demo_flag, logger = logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Get tick prices
            logger.debug("Getting tick prices")
            tick_prices = XTBData.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()-timedelta(minutes = 10), level = 0)
            price_a = tick_prices["BITCOIN"]["ask"]
            tick_prices = XTBData.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()-timedelta(minutes = 1), level = 0)
            price_b = tick_prices["BITCOIN"]["ask"]

            # Calculating rate of change
            roc = (price_b - price_a) / price_a * 100
            if roc > 0:
                cmd = 0
            else:
                cmd = 1





            # Check failure
            logger.debug("Checking failure conditions: wrtong cmd")
            with pytest.raises(Exception):
                trade_transaction = XTBData.tradeTransaction(symbol = "BITCOIN", volume=0.001, cmd = -1, price


            # Get trades history
            trades_history = XTBData.getTradesHistory(start = datetime.now()-timedelta(weeks = 52), end = datetime.now())

            orders = []
            for records in trades_history:
                orders.append(records['position'])

            # Get trades history
            logger.debug("Getting trades records")
            trades_records = XTBData.getTradeRecords(orders = orders)

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
            XTBData.delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")
                
    # Clear the captured logs
    caplog.clear()