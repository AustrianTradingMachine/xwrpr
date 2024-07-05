from config import XTB, generate_logger
import time

DEMO=False
logger=generate_logger(name="TEST",path='/home/philipp/Trading/XTB/Logger')

#print(XTB.WRAPPER_VERSION)
#print(XTB.API_VERSION)


XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

#version=XTBData.getVersion()

th=XTBData.getTradingHours(symbols=['EURUSD'])

#print(th)

XTBData.getCandles(symbol='EURUSD')

#XTBData.getTrades()

#TBData.getTickerPrices(symbol='EURJPY')
#XTBData.getTickerPrices(symbol='EURUSD')

#XTBData.getProfits()

#XTBData.getKeepAlive()


time.sleep(60*2)

XTBData.delete()

