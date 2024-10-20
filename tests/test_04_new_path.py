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
from pathlib import Path
import shutil
import xwrpr


# Path to the configuration directory
old_path = Path('~/.xwrpr').expanduser()/ 'user.ini'
new_path = Path('~/.xwrpr_new').expanduser()/ 'user.ini'

@pytest.fixture(scope = "function")
def setup_new_path():
    """
    Fixture to set up a new path for the configuration file.
    Copies the configuration file to a new path before the test and removes it after the test.
    """

    # Setup phase: Copy file to new path
    try:
        new_path.parent.mkdir(parents = True, exist_ok = True)
        shutil.copy(old_path, new_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {e}")
    except Exception as e:
        raise RuntimeError(f"Error copying file: {e}")

    # Yield control back to the test function
    yield new_path

    # Teardown phase: Remove the copied file after the test
    try:
        new_path.unlink()
    except FileNotFoundError as e:
        print(f"Cleanup error: File not found: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

def test_04_new_path(
        demo_flag: bool,
        log_level: int,
        caplog: pytest.LogCaptureFixture,
        capsys: pytest.CaptureFixture,
        setup_new_path: Path
) -> None:
    # Create a logger with the specified name
    logger = generate_logger(log_level)

    # Capture the logs
    with caplog.at_level(log_level):
        new_path = str(setup_new_path)
        logger.debug(f"New path: {new_path}")

        try:
            # Creating Wrapper
            logger.debug("Creating Wrapper with new path")
            xtb = xwrpr.Wrapper(demo = demo_flag, logger = logger, path = new_path)
        except Exception as e:
            logger.error("Error creating Wrapper: %s. Did you forget to enter your credentials?", e)
            pytest.fail(f"Failed to create Wrapper: {e}")


        try:
            # Get API version
            logger.debug("Getting API version")
            version = xtb.getVersion()

            # Check if the return value is a dict
            logger.debug("Checking if the return value is a dict")
            assert isinstance(version, dict), "Expected version to be a dict"
        finally:
            # Close Wrapper
            logger.debug("Closing Wrapper")
            xtb._delete()

    # Write records to log file
    with capsys.disabled():
        log_file_path = write_logs(caplog, __file__)
        print(f"\nLog files written to: {GREEN}{log_file_path}{RESET}\n")
            
    # Clear the captured logs
    caplog.clear()