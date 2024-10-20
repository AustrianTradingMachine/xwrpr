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
        # Skip the test if the demo flag is not set
        with capsys.disabled():
            print(f"\n{YELLOW}Skipping test as it requires a demo account{RESET}")
            print (f"\n{YELLOW}Run the test with \"pytest --demo\" flag to execute the test{RESET}")
            print (f"\n{YELLOW}Make sure your demo account is still active{RESET}\n")
        pytest.skip(reason = "Skipping test as it requires a demo account")

    # Skip the test if the trade flag is not set
    if not trade_flag:
        with capsys.disabled():
            print(f"\n{YELLOW}Skipping test as it requires your agreement for a trade{RESET}")
            print (f"\n{YELLOW}Run the test with \"pytest --trade\" flag if you agree to make this trade{RESET}")
        pytest.skip(reason = "Skipping test as it requires your agreement for a trade")

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
            # Get tick prices
            logger.debug("Getting tick prices")
            tick_prices = xtb.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()-timedelta(minutes = 5), level = 0)
            price_a = tick_prices["BITCOIN"]["ask"]
            tick_prices = xtb.getTickPrices(symbols = ["BITCOIN"], time = datetime.now()-timedelta(minutes = 1), level = 0)
            price_b = tick_prices["BITCOIN"]["ask"]

            # Calculating rate of change
            logger.debug("Calculating rate of change")
            roc = (price_b - price_a) / price_a
            if roc > 0:
                cmd = 4
                price = price_b+(price_b - price_a)*0.1
                sl = price_b-(price_b - price_a)*0.1
                tp = price_b+(price_b - price_a)*0.2
            else:
                cmd = 5
                price = price_b-(price_a-price_b)*0.1
                sl = price_b+(price_a-price_b)*0.1
                tp = price_b-(price_a-price_b)*0.2
            
            # Check failure
            logger.debug("Checking failure conditions: wrtong cmd")
            with pytest.raises(ValueError):
                trade_transaction = xtb.tradeTransaction(symbol = "BITCOIN", volume=0.001, cmd = -1, price = price, sl = sl, tp = tp, offset = 0, expiration = datetime.now()+timedelta(minutes = 1), type = 0, order = 0, custom_comment = "Test trade")
            logger.debug("Checking failure conditions: wrtong type")
            with pytest.raises(ValueError):
                trade_transaction = xtb.tradeTransaction(symbol = "BITCOIN", volume=0.001, cmd = cmd, price = price, sl = sl, tp = tp, offset = 0, expiration = datetime.now()+timedelta(minutes = 1), type = -1, order = 0, custom_comment = "Test trade")
            logger.debug("Checking failure conditions: expiration < now")
            with pytest.raises(ValueError):
                trade_transaction = xtb.tradeTransaction(symbol = "BITCOIN", volume=0.001, cmd = cmd, price = price, sl = sl, tp = tp, offset = 0, expiration = datetime.now()-timedelta(minutes = 1), type = 0, order = 0, custom_comment = "Test trade")
            logger.debug("Checking failure conditions: volume <= 0")
            with pytest.raises(ValueError):
                trade_transaction = xtb.tradeTransaction(symbol = "BITCOIN", volume=0, cmd = cmd, price = price, sl = sl, tp = tp, offset = 0, expiration = datetime.now()+timedelta(minutes = 1), type = 0, order = 0, custom_comment = "Test trade")

            # Make Trade
            logger.debug("Making trade")
            trade_transaction = xtb.tradeTransaction(symbol = "BITCOIN", volume=0.001, cmd = cmd, price = price, sl = sl, tp = tp, offset = 0, expiration = datetime.now()+timedelta(minutes = 1), type = 0, order = 0, custom_comment = "Test trade")

            # Check if the return value is a dictionary
            logger.debug("Checking if the return value is a dictionary")
            assert isinstance(trade_transaction, dict), "Expected trades history to be a dictionary"

            # Log the trade
            logger.debug("Logging the trade")
            details = ', '.join([f"{key}: {value}" for key, value in trade_transaction.items()])
            logger.info(details)


            # Verifying the trade
            logger.debug("Verifying the trade")
            trade_transaction_status = xtb.tradeTransactionStatus(order = trade_transaction["order"])

            # Check if the return value is a dictionary
            logger.debug("Checking if the return value is a dictionary")
            assert isinstance(trade_transaction_status, dict), "Expected trades history to be a dictionary"

            # Log the trade status
            logger.debug("Logging the trade status")
            details = ', '.join([f"{key}: {value}" for key, value in trade_transaction_status.items()])
            logger.info(details)

        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            xtb.delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")
                
    # Clear the captured logs
    caplog.clear()