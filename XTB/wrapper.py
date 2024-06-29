import logging
import os
from XTB.handler import HandlerManager
from XTB.utils import generate_logger

class Wrapper(HandlerManager):
    def __init__(self, demo: bool=True, logger=None):
        self._demo=demo

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger.getChild('XTB')
        else:
            self._logger=generate_logger(name='XTB', path=os.path.join(os.getcwd(), "logs"))

        super().__init__(demo=self._demo, logger = self._logger)


    def getAllSymbols(self):
        dh=self.get_DataHandler()

        response=dh.getData("AllSymbols")

        if not response:
            return False
        
        for symbol in response:
            print(symbol)

    def getVersion(self):
        dh=self.get_DataHandler()

        response=dh.getData("Version")

        if not response:
            return False
        





