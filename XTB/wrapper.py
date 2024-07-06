import logging
import os
import pandas as pd
from threading import Lock
import configparser
import datetime
import pytz
from XTB.handler import HandlerManager
from XTB.utils import generate_logger


# read api configuration
config = configparser.ConfigParser()
config.read('XTB/api.cfg')

SEND_INTERVAL=config.getint('CONNECTION','SEND_INTERVAL')


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

        self._deleted=False

        self._logger.info("Wrapper initialized")

    def __del__(self):
        self.delete()

    def delete(self):
        self._logger.info("Deleting wrapper.")
        super().delete()
        self._logger.info("Wrapper deleted.")

    def _open_stream_channel(self, **kwargs):
        sh=self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide stream channel")
            return False
        
        df=pd.DataFrame()
        lock=Lock()

        thread=sh.streamData(df=df, lock=lock, **kwargs)

        return df, lock, thread
    
    def getBalance(self):
        return self._open_stream_channel(command="Balance")

    def getCandles(self, symbol):
        return self._open_stream_channel(command="Candles", symbol=symbol)
    
    def getNews(self):
        return self._open_stream_channel(command="News")

    def getProfits(self):
        return self._open_stream_channel(command="Profits")

    def getTickPrices(self, symbol: str, minArrivalTime: int, maxLevel: int=1):
        if minArrivalTime < SEND_INTERVAL:
            minArrivalTime=SEND_INTERVAL
            self._logger.warning("minArrivalTime must be greater than " + str(SEND_INTERVAL) + ". Setting minArrivalTime to " + str(SEND_INTERVAL))

        if maxLevel < 1:
            maxLevel=1
            self._logger.warning("maxLevel must be greater than 1. Setting maxLevel to 1")

        return self._open_stream_channel(command="TickPrices", symbol=symbol, minArrivalTime=minArrivalTime, maxLevel=maxLevel)

    def getTrades(self):
        return self._open_stream_channel(command="Trades")
    
    def getTradeStatus(self):
        return self._open_stream_channel(command="TradeStatus")


    def _open_data_channel(self, **kwargs):
        dh=self.provide_DataHandler()
        if not dh:
            self._logger("Could not provide data channel")
            return False
        
        response = dh.getData(**kwargs)

        if not response:
            return False
        else:
            return response
        
    def getAllSymbols(self):
        return self._open_data_channel(command="AllSymbols")
    
    def getCalendar(self):
        return self._open_data_channel(command="Calendar")
    
    def getChartLastRequest(self, period: str, start: datetime, symbol: str):
        period_code=[
            "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"
        ]

        if period not in period_code:
            self._logger("Invalid period. Choose from: "+", ".join(period_code))
            return False
        
    
        
        


        return self._open_data_channel(command="ChartLastRequest", period=period, start=start, symbol=symbol)

    def getSymbol(self, symbol: str):
        return self._open_data_channel(command="Symbol")

    def getVersion(self):
        return self._open_data_channel(command="Version")









       
    
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





        
    
    def _to_time(self, timestamp: int) -> datetime.time:
        cet_datetime=self._to_datetime(timestamp)
        cet_time=cet_datetime.time()

        return cet_time

    def _cet_to_utc(self, cet_time: datetime.datetime) -> datetime.datetime:
        utc_time=cet_time.astimezone(self._utc_tz)

        return utc_time
