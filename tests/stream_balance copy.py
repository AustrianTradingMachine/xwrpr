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
from datetime import datetime
from dateutil.relativedelta import relativedelta


xtb = xwrpr.Wrapper(demo = False)
exchange = xtb.streamBalance()

stop_time = datetime.now() + relativedelta(seconds=10)
while datetime.now() < stop_time:
    data = exchange['queue'].get()

    # Log the data
    details = ', '.join([f"{key}: {value}" for key, value in data.items()])

# Stop the stream

exchange['thread'].stop()
xtb.delete()