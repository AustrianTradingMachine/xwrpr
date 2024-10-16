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

from helper.helper import generate_logger
import xwrpr
from datetime import datetime, timedelta

# Setting DEMO to True will use the demo account
DEMO=False

# Create a logger with the specified name
logger = generate_logger(filename=__file__)

try:
    # Creating Wrapper
    XTBData=xwrpr.Wrapper(demo=DEMO, logger=logger)
except Exception as e:
    logger.error("Error creating Wrapper: %s", e)
    logger.info("Did you forget to enter your credentials?")
    logger.info("Look in README.md for more information")
    exit()

# Check failure
try:
    records= XTBData.getChartLastRequest(symbol="GOLD", period="M1", start=datetime.now()+timedelta(days=1))
    raise Exception("Failure Check: start > now")
except Exception as e:
    logger.error("Failure Check: start > now")
    logger.error(e)

try:
    records= XTBData.getChartLastRequest(symbol="GOLD", period="X1", start=datetime.min)
    raise Exception("Failure Check: period not in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1']")
except Exception as e:
    logger.error("Failure Check: period not in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1']")
    logger.error(e)   

# Get chart
for period in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]:
    records= XTBData.getChartLastRequest(symbol="GOLD", period=period, start=datetime.min)

    # Check if the return value is a dictionary
    if not isinstance(records, dict):
        logger.error("Error getting calendar")
        continue

    # Print chart
    for record in records["rateInfos"]:
        line = ''
        for key, value in record.items():
            line += key + ': ' + str(value) + ', '
        logger.info(line)

# Close Wrapper
XTBData.delete()