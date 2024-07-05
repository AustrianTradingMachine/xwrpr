import logging
import os
import datetime
import pytz
from XTB.handler import HandlerManager
from XTB.utils import generate_logger

class Wrapper(HandlerManager):
    def __init__(self, demo: bool=True, logger=None):
        self._demo=demo

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger.getChild('Wrp')
        else:
            self._logger=generate_logger(name='Wrp', path=os.path.join(os.getcwd(), "logs"))

        self._logger.info("Initializing wrapper")

        self._utc_tz = pytz.utc
        self._cest_tz = pytz.timezone('Europe/Berlin')

        super().__init__(demo=self._demo, logger = self._logger)

        self._running=dict()

        self._logger.info("Wrapper initialized")

    def __del__(self):
        self.delete()

    def delete(self):
        self._logger.info("Deleting wrapper.")
        super().delete()
        self._logger.info("Wrapper deleted.")

    def getTickerPrices(self, symbol: str) -> dict:
        sh=self.provide_StreamHandler()

        sh.streamData("TickerPrices", symbol=symbol)

    def getKeepAlive(self) -> dict:
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide data")
            return False

        response=sh.streamData("KeepAlive")
        if not response:
            return False

        return response
    
    def getTrades(self) -> dict:
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide data")
            return False

        response=sh.streamData("Trades")
        if not response:
            return False
        
    def getProfits(self) -> dict:
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide data")
            return False

        response=sh.streamData("Profits")
        if not response:
            return False
        

    def getBalance(self) -> dict:
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide data")
            return False

        response=sh.streamData("Balance")
        if not response:
            return False

        return response
    
    def getCandles(self, symbol) -> dict:
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide data")
            return False

        response=sh.streamData("Candles", symbol=symbol)
        if not response:
            return False

        return response

    def getSymbols(self) ->dict:
        dh=self.provide_DataHandler()
        response=dh.getData("AllSymbols")
        if not response:
            return False

        return response

    def getVersion(self) -> dict:
        dh=self.provide_DataHandler()
        if not dh:
            self._logger("Could not provide data")
            return False

        response=dh.getData("Version")
        if not response:
            return False
        
        version=response['version']
        major, minor, patch = version.split('.')

        return {'major': major, 'minor': minor, 'patch': patch}
    
    def getTradingHours(self, symbols: list) -> dict:
        dh=self.provide_DataHandler()
        response=dh.getData("TradingHours", symbols=symbols)
        if not response:
            return False
        
        data_dict={}
        for record in response:
            symbol = record['symbol']
            quotes = record['quotes']
            trading = record['trading']

            data_dict[symbol]={'quotes': {}, 'trading': {}}

            for quote in quotes:
                time_f = self._to_time(timestamp=quote['fromT']).strftime('%H:%M:%S')
                time_t = self._to_time(timestamp=quote['toT']).strftime('%H:%M:%S')

                data_dict[symbol]['quotes'][quote['day']]={'from': time_f, 'to': time_t}

            for trade in trading:
                time_f = self._to_time(timestamp=trade['fromT']).strftime('%H:%M:%S')
                time_t = self._to_time(timestamp=trade['toT']).strftime('%H:%M:%S')

                data_dict[symbol]['trading'][trade['day']]={'from': time_f, 'to': time_t}

        return data_dict



    def _to_datetime(self, timestamp: int) -> datetime.datetime:
        timestamp=timestamp/1000
        cet_datetime=datetime.datetime.fromtimestamp(timestamp, tz=self._utc_tz)

        return cet_datetime
    
    def _to_time(self, timestamp: int) -> datetime.time:
        cet_datetime=self._to_datetime(timestamp)
        cet_time=cet_datetime.time()

        return cet_time

    def _cet_to_utc(self, cet_time: datetime.datetime) -> datetime.datetime:
        utc_time=cet_time.astimezone(self._utc_tz)

        return utc_time