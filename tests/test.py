from config import XTB, generate_logger
import time

DEMO=False
logger=generate_logger(name="TEST",path='/home/philipp/Trading/XTB/Logger')

#print(XTB.WRAPPER_VERSION)
#print(XTB.API_VERSION)


XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

if False:
    alls=XTBData.getAllSymbols()

    for record in alls:
        logger.info(record['symbol']+" "+record['categoryName']+" "+record['description'])

version=XTBData.getVersion()

print(version)

#th=XTBData.getTradingHours(symbols=['ETHEREUM'])

#print(th)

XTBData.getCandles(symbol='ETHEREUM')

#XTBData.getBalance()

#XTBData.getNews()

XTBData.getTickPrices(symbol='ETHEREUM', minArrivalTime=0, maxLevel=1)

#XTBData.getTrades()

#TBData.getTickerPrices(symbol='EURJPY')
#XTBData.getTickerPrices(symbol='EURUSD')

#XTBData.getProfits()



time.sleep(60*1)

XTBData.delete()

