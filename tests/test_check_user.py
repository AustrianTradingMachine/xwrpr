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

import xwrpr
from pathlib import Path


# Setting DEMO to True will use the demo account
DEMO=False


# just example how to generate alogger. Feel free to use your own logger
logger=xwrpr.generate_logger(name="TEST_check_user",path=Path('~/Logger/xwrpr').expanduser())


# Creating Wrapper
XTBData=xwrpr.Wrapper(demo=DEMO, logger=logger)


# getting API version
version=XTBData.getVersion()

if version['version'] != xwrpr.API_VERSION:
    print("API version is different")
else:
    print("API version is correct")


# get user data
user=XTBData.getCurrentUserData()
print(user)


# get server time
server=XTBData.getServerTime()
print(server)


# Close Wrapper
XTBData.delete()
