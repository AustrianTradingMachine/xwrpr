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
from helper.helper import generate_logger, demo_flag
import xwrpr
from datetime import datetime, timedelta
import logging


def test_7_get_chart_last_request(demo_flag):
    # Create a logger with the specified name
    logger = generate_logger(filename=__file__)

    try:
        # Creating Wrapper
        XTBData=xwrpr.Wrapper(demo=demo_flag, logger=logger)
    except Exception as e:
        logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
        pytest.fail(f"Failed to create Wrapper: {e}")

    try:
        # Check failure
        with pytest.raises(Exception):
            records= XTBData.getChartLastRequest(symbol="GOLD", period="M1", start=datetime.now()+timedelta(days=1))
        with pytest.raises(Exception):
            records= XTBData.getChartLastRequest(symbol="GOLD", period="X1", start=datetime.min)

        # Get chart
        for period in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]:
            records= XTBData.getChartLastRequest(symbol="GOLD", period=period, start=datetime.min)

            # Check if the return value is a dictionary
            assert isinstance(records, dict), "Expected records to be a dict"

            # Print chart
            logger.setLevel(logging.INFO)
            for record in records["rateInfos"]:
                details = ', '.join([f"{key}: {value}" for key, value in record.items()])
                logger.info(details)
    finally:
        # Close Wrapper
        XTBData.delete()