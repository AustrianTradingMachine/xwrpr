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

import logging
import xwrpr

# Setting DEMO to True will use the demo account
DEMO=False


# Create a logger with the specified name
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

try:
    # Creating Wrapper 1
    XTBData_1=xwrpr.Wrapper(demo=DEMO, logger=logger)
except Exception as e:
    logger.error("Error creating Wrapper: %s", e)
    logger.info("Did you forget to enter your credentials?")
    logger.info("Look in README.md for more information")
    exit()

# Creating Wrapper 2
XTBData_2=xwrpr.Wrapper(demo=DEMO, logger=logger)


# getting API version
version=XTBData_1.getVersion()

# getting API version
version=XTBData_2.getVersion()

# Close Wrapper 1
XTBData_1.delete()

# Close Wrapper 2
XTBData_2.delete()