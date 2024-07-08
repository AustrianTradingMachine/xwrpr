from config import XTB, generate_logger
import time
from datetime import datetime, timedelta

DEMO=False
#DEMO=True

# just example how to generate alogger. Feel free to use your own logger
logger=generate_logger(name="TEST",path='/home/philipp/Trading/XTBpy/Logger')
#logger=generate_logger(name="TEST",path='~/XTBpy/Logger')

print(XTB.__version__)
print(XTB.API_VERSION)


XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# getting API version
version=XTBData.getVersion()

if version['version'] != XTB.API_VERSION:
    print("API version is different")

# gettinbg all symbols
#alls=XTBData.getAllSymbols()

#for record in alls:
#    print(record['symbol']+" "+record['categoryName']+" "+record['description'])

# getting chart history
chart=XTBData.getChartRangeRequest(period='M15', symbol='EURUSD', end=datetime.now(), start=datetime.now() - timedelta(days=30))

for candle in chart['rateInfos']:
    print("open " + str(candle['open']) + " high " + str(candle['high']) + " low " + str(candle['low']) + " close " + str(candle['close']) + " volume " + str(candle['vol']) + " time " + candle['ctmString'])

# getting the Trading Hours
th=XTBData.getTradingHours(symbols=['EURUSD'])

print(th)

# Streaming data an reading the df
control=XTBData.streamTickPrices(symbol='ETHEREUM', minArrivalTime=0, maxLevel=1)

later = datetime.now() + timedelta(seconds=60*5)
while datetime.now() < later:
    control['lock'].acquire(blocking=True)
    if not control['df'].empty:
        print(control['df'])
        control['df'] = control['df'].iloc[0:0]
    control['lock'].release()
    time.sleep(1)

control['thread'].join()


XTBData.delete()