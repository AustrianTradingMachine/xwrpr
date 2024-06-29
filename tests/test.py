from config import XTB, generate_logger
DEMO=True

logger=generate_logger(name="XTB",path='/home/philipp/Trading/XTB/Logger')

print(XTB.WRAPPER_VERSION)
print(XTB.API_VERSION)


XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

major, minor, patch=XTBData.getVersion()

print(f"Major: {major}, Minor: {minor}, Patch: {patch}")

del XTBData