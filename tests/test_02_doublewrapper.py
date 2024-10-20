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
from tests.helper import generate_logger, write_logs, GREEN, RESET
import xwrpr


def test_02_doublewrapper(
        demo_flag: bool,
        log_level: int,
        caplog: pytest.LogCaptureFixture,
        capsys: pytest.CaptureFixture,
) -> None:
    # Create a logger with the specified name
    logger = generate_logger(log_level)

    # Capture the logs
    with caplog.at_level(log_level):
        try:
            # Creating Wrapper 1
            logger.debug("Creating Wrapper 1")
            xtb_1 = xwrpr.Wrapper(demo = demo_flag, logger = logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")

        try:
            # Creating Wrapper 2
            logger.debug("Creating Wrapper 2")
            xtb_2 = xwrpr.Wrapper(demo = demo_flag, logger = logger)
        except Exception as e:
            logger.error("Error creating Wrapper: %s", e)
            pytest.fail(f"Failed to create Wrapper: {e}")
        finally:
            # Close Wrapper 1
            logger.debug("Closing Wrapper 1")
            xtb_1._delete()

        try:
            # Getting API version with Wrapper 1
            logger.debug("Getting API version with Wrapper 1")
            version_1 = xtb_1.getVersion()

            # Getting API version with Wrapper 2
            logger.debug("Getting API version with Wrapper 2")
            version_2 = xtb_2.getVersion()

            # Check if the return values of both Wrappers are dicts
            logger.debug("Checking if the return values are dicts with Wrapper 1")
            assert isinstance(version_1, dict), "Expected version from Wrapper 1 to be a dict"
            logger.debug("Checking if the return values are dicts with Wrapper 2")
            assert isinstance(version_2, dict), "Expected version from Wrapper 2 to be a dict"
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper 1")
            xtb_1._delete()
            logger.debug("Closing Wrapper 2")
            xtb_2._delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")
            
    # Clear the captured logs
    caplog.clear()