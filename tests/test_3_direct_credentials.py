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
import configparser
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
log_file_path = Path(__file__).parent.absolute()/'logs'/__file__.split('/')[-1].replace('.py', '.log')
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Read the configuration file
config = configparser.ConfigParser()
config_path = Path('~/.xwrpr').expanduser()/'user.ini'
config.read(config_path)

USERNAME = config.get('USER', 'REAL_ID')
PASSWORD = config.get('USER', 'PASSWORD')

try:
    # Creating Wrapper
    XTBData=xwrpr.Wrapper(demo=DEMO, logger=logger, username=USERNAME, password=PASSWORD)
except Exception as e:
    logger.error("Error creating Wrapper: %s", e)
    logger.info("Did you forget to enter your credentials?")
    logger.info("Look in README.md for more information")
    exit()

# getting API version
version=XTBData.getVersion()

# Close Wrapper
XTBData.delete()