from handler import DataHandler, StreamHandler
from utils import set_logger

class Wrapper(DataHandler, StreamHandler):
    def __init__(self, demo: bool=True, name: str=None, logger = None):
        if name and logger:
            raise ValueError("You can either provide 'name' or 'logger', but not both.")
        
        if name:
            self._name = name
            self._logger = set_logger(self._name)
        elif logger:
            self._logger = logger
            self._name = None
        else:
            raise ValueError("You must provide either 'name' or 'logger'.")

        self._demo=demo
        super().__init__(demo=self._demo, logger = self._logger)

    def __del__(self):
        self.delete()

    def getAllSymbols(self):
        response=self.getData("AllSymbols")

        if not response:
            return False
        
        for symbol in response:
            print(symbol)

    def getVersion(self):
        response=self.getData("Version")

        if not response:
            return False
        
        for symbol in response:
            print(symbol)
        