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
from datetime import datetime

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

# Get market events
for period in 
chart_range=XTBData.getChartLastRequest(symbol='GOLD', period="M1", start=datetime.min)

# Check if the return value is a list
if not isinstance(calendar, list):
    logger.error("Error getting calendar")
    exit()

# Print all events
for event in calendar:
    logger.info("")
    logger.info("Title: %s", event['title'])
    line = ''
    for key, value in event.items():
        line += key + ': ' + str(value) + ', '
    logger.info(line)

# Close Wrapper
XTBData.delete()