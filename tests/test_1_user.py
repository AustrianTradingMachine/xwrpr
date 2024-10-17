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
from helper.helper import generate_logger
import xwrpr

# Setting DEMO to True will use the demo account
DEMO=False

def test_1_user():
    # Create a logger with the specified name
    logger = generate_logger(filename=__file__)

    try:
        # Creating Wrapper
        XTBData=xwrpr.Wrapper(demo=DEMO, logger=logger)
    except Exception as e:
        logger.error("Error creating Wrapper: %s", e)
        logger.info("Did you forget to enter your credentials?")
        logger.info("Look in README.md for more information")
        pytest.fail(f"Failed to create Wrapper: {e}")

    # getting API version
    version=XTBData.getVersion()

    # Check if the return value is a dict
    assert isinstance(version, dict), "Expected commission to be a dict"

    # Check if the API version matches the expected version
    assert version['version'] == xwrpr.API_VERSION, \
        f"API version is different. Is {version['version']}, should be {xwrpr.API_VERSION}"
    
    logger.info("API version is correct")

    # Close Wrapper
    XTBData.delete()