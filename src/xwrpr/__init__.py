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

Classes:
    Wrapper: The main class of the xwrpr package.

Functions:
    None

Constants:
    API_VERSION: The version of the XTB API the xwrpr relies on.
"""

import sys
from importlib.metadata import version, PackageNotFoundError
from xwrpr.wrapper import Wrapper


# Ensure the script is being run with Python 3.9 or higher
if sys.version_info < (3, 9):
    raise RuntimeError("The xwrpr package requires Python 3.9 or higher.")
# Ensure the script is being run with Python 3
if sys.version_info[0] != 3:
    raise RuntimeError("The xwrpr package requires Python 3.")

# Define the XTB Api version the xwrpr relies on
API_VERSION = '2.5.0'

# Get the version dynamically from the package metadata
try:
    __version__ = version("xwrpr")
except PackageNotFoundError:
    __version__ = "unknown"

# Define what should be imported when using 'from xwrpr import *'
__all__ = ['Wrapper', 'API_VERSION']