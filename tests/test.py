#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    XTBpy, a wrapper for the API of XTB (https://www.xtb.com)
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

from config import XTB, generate_logger
import time
from datetime import datetime, timedelta

DEMO=True

# just example how to generate alogger. Feel free to use your own logger
logger=generate_logger(name="TEST",path='~/Logger/XTBpy')

print(XTB.__version__)
print(XTB.API_VERSION)


# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# getting API version
version=XTBData.getVersion()

if version['version'] != XTB.API_VERSION:
    print("API version is different")

# gettinbg all symbols
alls=XTBData.getAllSymbols()

for record in alls:
    print(record['symbol']+" "+record['categoryName']+" "+record['description'])

# getting chart history
chart=XTBData.getChartRangeRequest(period='M15', symbol='EURUSD', end=datetime.now(), start=datetime.now() - timedelta(days=30))

for candle in chart['rateInfos']:
    print("open " + str(candle['open']) + " high " + str(candle['high']) + " low " + str(candle['low']) + " close " + str(candle['close']) + " volume " + str(candle['vol']) + " time " + candle['ctmString'])

# getting the Trading Hours
th=XTBData.getTradingHours(symbols=['EURUSD'])

print(th)

# Streaming data an reading the df
exchange=XTBData.streamTickPrices(symbol='ETHEREUM', minArrivalTime=0, maxLevel=1)

later = datetime.now() + timedelta(seconds=60*1)
while datetime.now() < later:
    exchange['lock'].acquire(blocking=True)
    if not exchange['df'].empty:
        print(exchange['df'].to_string(index=False, header=False))
        exchange['df'] = exchange['df'].iloc[0:0]
    exchange['lock'].release()
    time.sleep(1)

exchange['thread'].start()

# Close Wrapper
XTBData.delete()
