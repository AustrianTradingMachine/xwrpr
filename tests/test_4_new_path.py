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
from pathlib import Path
import shutil
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

# Path to the configuration directory
old_path = Path('~/.xwrpr').expanduser()/ 'user.ini'
new_path = Path('~/.xwrpr_new').expanduser()/ 'user.ini'


# Create new path
new_path.parent.mkdir(parents=True, exist_ok=True)

# Copy file
try:
    shutil.copy(old_path, new_path)
    logger.info(f"Copied {old_path} to {new_path}")
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
except Exception as e:
    logger.error(f"Error copying file: {e}")

try:
    # Creating Wrapper
    XTBData=xwrpr.Wrapper(demo=DEMO, logger=logger, path=new_path)
except Exception as e:
    logger.error("Error creating Wrapper: %s", e)
    logger.info("Did you forget to enter your credentials?")
    logger.info("Look in README.md for more information")
    exit()

# getting API version
version=XTBData.getVersion()

# Close Wrapper
XTBData.delete()

# Remove new path
try:
    new_path.unlink()
    logger.info(f"Removed {new_path}")
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")