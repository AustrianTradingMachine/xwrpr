from config import XTB, generate_logger
DEMO=True

logger=generate_logger(name="XTB",path='/home/philipp/Trading/XTB/Logger')

XTBData=XTB.XTB(demo=DEMO, logger=logger)

XTBData.getVersion()

del XTBData