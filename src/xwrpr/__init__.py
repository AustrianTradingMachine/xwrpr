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

"""
xwrpr - A wrapper for the API of XTB (https://www.xtb.com)

This module provides a Wrapper class to interact with the XTB API.
"""

import sys
from importlib.metadata import version, PackageNotFoundError
from xwrpr.wrapper import Wrapper

# Ensure the script is being run with Python 3.9 or higher
if sys.version_info < (3, 9):
    raise RuntimeError("xwrpr requires Python 3.9 or higher")

# Define the XTB Api version the xwrpr relies on
API_VERSION = '2.5.0'

# Get the version dynamically from the package metadata
try:
    __version__ = version("xwrpr")
except PackageNotFoundError:
    __version__ = "unknown"

# Define what is exported when `from xwrpr import *` is used
__all__ = ['Wrapper', 'API_VERSION']
