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
import logging


def test_9_get_commission_def(demo_flag):
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
            commission= XTBData.getCommissionDef(symbol="GOLD", volume=-0)

        # Get commission definition
        commission= XTBData.getCommissionDef(symbol="GOLD", volume=1)

        # Check if the return value is a dict
        assert isinstance(commission, dict), "Expected commission to be a dict"

        # Print commission definition
        logger.setLevel(logging.INFO)
        logger.info("Commission Definition")
        details = ', '.join([f"{key}: {value}" for key, value in commission.items()])
        logger.info(details)
    finally:
        # Close Wrapper
        XTBData.delete()