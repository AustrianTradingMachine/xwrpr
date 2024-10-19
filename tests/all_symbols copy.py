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
import time
from datetime import datetime, timedelta

print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "Creating Wrapper")
XTBData = xwrpr.Wrapper(demo = False)
#all_symbols = XTBData.getAllSymbols()
XTBData.getNews(start = datetime.now()-timedelta(days = 2), end = datetime.now())
print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "Done")