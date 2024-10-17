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
from helper.helper import generate_logger, write_logs, demo_flag
import logging
import xwrpr
from datetime import datetime, timedelta


def test_11_get_ibs_history(demo_flag, caplog):
    # Create a logger with the specified name
    logger = generate_logger()

    with caplog.at_level(logging.DEBUG):
        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper")
            XTBData=xwrpr.Wrapper(demo=demo_flag, logger=logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Check failure
            logger.debug("Checking failure conditions: end > now")
            with pytest.raises(Exception):
                history= XTBData.getIbsHistory(start=datetime.now()-timedelta(days=2), end=datetime.now()+timedelta(days=1))
            logger.debug("Checking failure conditions: start > end")
            with pytest.raises(Exception):
                history= XTBData.getIbsHistory(start=datetime.now(), end=datetime.now()-timedelta(days=2))
            logger.debug("Checking failure conditions: deprecated function")
            with pytest.raises(Exception):
                history= XTBData.getIbsHistory(start=datetime.now()-timedelta(days=2), end=datetime.now()-timedelta(days=1))
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            XTBData.delete()

    # Write records to log file
    write_logs(caplog, __file__)