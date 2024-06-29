from wrapper import DataWrapper
import time


DEMO=False



XTBData=DataWrapper(name="data1",demo=DEMO)

XTBData.getVersion()

del XTBData