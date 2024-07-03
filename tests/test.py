from config import XTB, generate_logger
import time

DEMO=True

logger=generate_logger(name="TEST",path='/home/philipp/Trading/XTB/Logger')

#print(XTB.WRAPPER_VERSION)
#print(XTB.API_VERSION)


XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

version=XTBData.getVersion()

print('major:', version['major'])
print('minor:', version['minor'])
print('patch:', version['patch'])

th=XTBData.getTradingHours(symbols=['EURUSD'])

print(th)

XTBData.getCandles(symbol='EURUSD')


time.sleep(5)

XTBData.delete()

