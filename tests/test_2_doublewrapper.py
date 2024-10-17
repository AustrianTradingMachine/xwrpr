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


def test_2_doublewrapper(demo_flag):
    # Create a logger with the specified name
    logger = generate_logger(filename=__file__)

    try:
        # Creating Wrapper 1
        XTBData_1=xwrpr.Wrapper(demo=demo_flag, logger=logger)
    except Exception as e:
        logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
        pytest.fail(f"Failed to create Wrapper: {e}")

    try:
        # Creating Wrapper 2
        XTBData_2=xwrpr.Wrapper(demo=demo_flag, logger=logger)
    except Exception as e:
        logger.error("Error creating Wrapper: %s", e)
        pytest.fail(f"Failed to create Wrapper: {e}")
    finally:
        # Close Wrapper
        XTBData_1.delete()

    try:
        # getting API version
        version_1=XTBData_1.getVersion()
        version_2=XTBData_2.getVersion()

        # Check if the return values are dicts
        assert isinstance(version_1, dict), "Expected version from Wrapper 1 to be a dict"
        assert isinstance(version_2, dict), "Expected version from Wrapper 2 to be a dict"
    finally:
        # Close Wrapper
        XTBData_1.delete()
        XTBData_2.delete()