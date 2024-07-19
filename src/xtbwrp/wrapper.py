#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###########################################################################
#
#    xwrpr - A wrapper for the API of XTB (https://www.xtb.com)
#
#    Copyright (C) 2024  Philipp Craighero
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###########################################################################

import logging
import pandas as pd
from threading import Lock
from pathlib import Path
import configparser
from datetime import datetime
from dateutil.relativedelta import relativedelta
from xwrpr.handler import HandlerManager
from xwrpr.utils import generate_logger, calculate_timedelta, datetime_to_unixtime


# read api configuration
config = configparser.ConfigParser()
config_path=Path(__file__).parent.absolute()/ 'api.ini'
config.read(config_path)

SEND_INTERVAL=config.getint('CONNECTION','SEND_INTERVAL')


class Wrapper(HandlerManager):
    """
    Wrapper class for XTB API.

    Attributes:
        _demo (bool): Flag indicating whether the demo environment is used.
        _logger (logging.Logger): Logger instance for logging messages.
        _deleted (bool): Flag indicating whether the wrapper has been deleted.

    Methods:
        __init__(self, demo: bool=True, logger=None): Initializes the Wrapper instance.
        __del__(self): Destructor method that calls the delete() method.
        delete(self): Deletes the wrapper instance.
        _open_stream_channel(self, **kwargs): Opens a stream channel for data streaming.
        streamBalance(self): Retrieves the balance data.
        streamCandles(self, symbol: str): Retrieves the candle data for a specific symbol.
        streamNews(self): Retrieves the news data.
        streamProfits(self): Retrieves the profits data.
        streamTickPrices(self, symbol: str, minArrivalTime: int, maxLevel: int=1): Retrieves the tick prices data.
        streamTrades(self): Retrieves the trades data.
        streamradeStatus(self): Retrieves the trade status data.
        _open_data_channel(self, **kwargs): Opens a data channel for data retrieval.
        getAllSymbols(self): Retrieves all symbols data.
        getCalendar(self): Retrieves the calendar data.
        getChartLastRequest(self, symbol: str, period: str, start: datetime=None): Retrieves the last chart data request.
        getChartRangeRequest(self, symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0): Retrieves the chart data within a range.
        getCommissionDef(self, symbol: str, volume: float): Retrieves the commission definition data.
        getCurrentUserData(self): Retrieves the current user data.
        getIbsHistory(self, start: datetime, end: datetime): Retrieves the IBS history data.
        getMarginLevel(self): Retrieves the margin level data.
        getMarginTrade(self, symbol: str, volume: float): Retrieves the margin trade data.
        getNews(self): Retrieves the news data.
        getProfitCalculation(self, symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int): Retrieves the profit calculation data.
        getServerTime(self): Retrieves the server time data.
        getStepRules(self): Retrieves the step rules data.
    """

    def __init__(self, demo: bool=True, logger=None):
        """
        Initializes the wrapper object.

        Args:
            demo (bool, optional): Specifies whether to use the demo mode. Defaults to True.
            logger (logging.Logger, optional): The logger object to use for logging. 
                If not provided, a new logger will be created. Defaults to None.

        """
        self._demo=demo

        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger.getChild('Wrp')
        else:
            self._logger=generate_logger(name='Wrp', path=Path.cwd() / "logs")

        self._logger.info("Initializing wrapper")

        super().__init__(demo=self._demo, logger = self._logger)

        self._deleted=False

        self._logger.info("Wrapper initialized")

    def __del__(self):
        """
        Destructor method for the XTB wrapper class.
        This method is automatically called when the object is about to be destroyed.
        It performs cleanup operations and deletes the object.

        """
        self.delete()

    def delete(self):
        """
        Deletes the wrapper.

        If the wrapper has already been deleted, a warning message is logged and the method returns True.

        Returns:
            bool: True if the wrapper is successfully deleted, False otherwise.

        """
        if self._deleted:
            self._logger.warning("Wrapper already deleted.")
            return True

        self._logger.info("Deleting wrapper.")
        super().delete()
        self._logger.info("Wrapper deleted.")

    def _open_stream_channel(self, **kwargs):
        """
        Opens a stream channel for receiving data.

        Args:
            **kwargs: Additional keyword arguments to be passed to the `streamData` method.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        """
        sh = self.provide_StreamHandler()
        if not sh:
            self._logger("Could not provide stream channel")
            return False
        
        df = pd.DataFrame()
        lock = Lock()

        exchange = {'df': df, 'lock': lock}
        sh.streamData(exchange=exchange, **kwargs)

        return exchange
    
    def streamBalance(self):
        """
        Allows to get actual account indicators values in real-time, as soon as they are available in the system.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe: 
            name	            type	    description
            balance	            float	    balance in account currency
            credit	            float	    credit in account currency
            equity	            float	    sum of balance and all profits in account currency
            margin	            float	    margin requirements
            marginFree	        float	    free margin
            marginLevel	        float	    margin level percentage

        """
        return self._open_stream_channel(command="Balance")

    def streamCandles(self, symbol: str):
        """
        Subscribes for and unsubscribes from API chart candles. The interval of every candle is 1 minute. A new candle arrives every minute

        Parameters:
        symbol (str): The symbol for which to retrieve the candles.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe: 
            name	            type	    description
            close	            float	    Close price in base currency
            ctm	                timestamp	Candle  start time in CET time zone (Central European Time)
            ctmString	        string	    String representation of the ctm field
            high	            float	    Highest value in the given period in base currency
            low	                float	    Lowest  value in the given period in base currency
            open	            float	    Open price in base currency
            quoteId	            integer     Source of price
            symbol	            string	    Symbol
            vol	                float	    Volume in lots

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        """
        return self._open_stream_channel(command="Candles", symbol=symbol)
    
    def streamNews(self):
        """
        Subscribes for and unsubscribes from news.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe: 
            name	            type	    description
            body	            string	    Body
            key	                string	    News key
            time	            timestamp   Time
            title	            string	    News title

        """
        return self._open_stream_channel(command="News")

    def streamProfits(self):
        """
        Subscribes for and unsubscribes from profits.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe: 
            name	            type	    description
            order	            integer 	Order number
            order2	            integer     Transaction ID
            position	        integer     Position number
            profit	            float	    Profit in account currency

        """
        return self._open_stream_channel(command="Profits")

    def streamTickPrices(self, symbol: str, minArrivalTime: int, maxLevel: int=1):
        """
        Establishes subscription for quotations and allows to obtain the relevant information in real-time, as soon as it is available in the system.

        Args:
            symbol (str): The symbol for which to retrieve tick prices.
            minArrivalTime (int): The minimum arrival time for the tick prices.
            maxLevel (int, optional): The maximum level of tick prices to retrieve. Defaults to 1.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe:
            name	            type	    description
            ask	                float	    Ask price in base currency
            askVolume	        integer     Number of available lots to buy at given price or null if not applicable
            bid	                float	    Bid price in base currency
            bidVolume	        integer 	Number of available lots to buy at given price or null if not applicable
            high	            float	    The highest price of the day in base currency
            level	            integer 	Price level
            low	                float	    The lowest price of the day in base currency
            quoteId	            integer     Source of price, detailed description below
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            symbol	            string	    Symbol
            timestamp	        timestamp   Timestamp

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        """
        if minArrivalTime < SEND_INTERVAL:
            minArrivalTime=SEND_INTERVAL
            self._logger.warning("minArrivalTime must be greater than " + str(SEND_INTERVAL) + ". Setting minArrivalTime to " + str(SEND_INTERVAL))

        if maxLevel < 1:
            maxLevel=1
            self._logger.warning("maxLevel must be greater than 1. Setting maxLevel to 1")

        return self._open_stream_channel(command="TickPrices", symbol=symbol, minArrivalTime=minArrivalTime, maxLevel=maxLevel)

    def streamTrades(self):
        """
        Establishes subscription for user trade status data and allows to obtain the relevant information in real-time, as soon as it is available in the system.
        New  are sent by streaming socket only in several cases:
            - Opening the trade
            - Closing the trade
            - Modification of trade parameters
            - Explicit trade update done by server system to synchronize data.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe:
            Dictionary with the following fields:
            name	            type	    description
            close_price	        float	    Close price in base currency
            close_time	        timestamp   Null if order is not closed
            closed	            boolean	    Closed
            cmd	                integer     Operation code
            comment	            string	    Comment
            commission	        float	    Commission in account currency, null if not applicable
            customComment	    string	    The value the customer may provide in order to retrieve it later.
            digits	            integer     Number of decimal places
            expiration	        timestamp	Null if order is not closed
            margin_rate	        float	    Margin rate
            offset	            integer     Trailing offset
            open_price	        float	    Open price in base currency
            open_time	        timestamp	Open time
            order	            integer 	Order number for opened transaction
            order2	            integer     Transaction id
            position	        integer     Position number (if type is 0 and 2) or transaction parameter (if type is 1)
            profit	            float	    null unless the trade is closed (type=2) or opened (type=0)
            sl	                float	    Zero if stop loss is not set (in base currency)
            state	            string	    Trade state, should be used for detecting pending order's cancellation
            storage	            float	    Storage
            symbol	            string	    Symbol
            tp	                float	    Zero if take profit is not set (in base currency)
            type	            integer     type
            volume	            float	    Volume in lots

        Possible values of cmd field:
            name	            value	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        Possible values of comment field:
            - "[S/L]", then the trade was closed by stop loss
            - "[T/P]", then the trade was closed by take profit
            - "[S/O margin level% equity / margin (currency)]", then the trade was closed because of Stop Out
            - If the comment remained unchanged from that of opened order, then the order was closed by user

        Possible values of state field:
            name	            value	    description
            MODIFIED	        "Modified"  modified
            DELETED	            "Deleted"   deleted

        Possible values of type field:
            name	            value	    description
            OPEN	            0	        order open, used for opening orders
            PENDING	            1	        order pending, only used in the streaming getTrades  command
            CLOSE	            2	        order close
            MODIFY	            3	        order modify, only used in the tradeTransaction  command
            DELETE	            4	        order delete, only used in the tradeTransaction  command

        
        """
        return self._open_stream_channel(command="Trades")
    
    def streamTradeStatus(self):
        """
        Allows to get status for sent trade requests in real-time, as soon as it is available in the system.

        Returns:
            A dictionary, containing the following elements:
                - df (pandas.DataFrame): The DataFrame to store the streamed data.
                - lock (threading.Lock): A lock object for synchronization of DataFrame Access.
                - thread (Thread): Starting the Thread will terminate the stream

        Format of Dataframe:
            Dictionary with the following fields:
            name	            type	    description
            customComment	    string	    The value the customer may provide in order to retrieve it later.
            message	            string	    Can be null
            order	            integer     Unique order number
            price	            float	    Price in base currency
            requestStatus	    integer     Request status code, described below

        """
        return self._open_stream_channel(command="TradeStatus")

    def _open_data_channel(self, **kwargs):
        """
        Opens a data channel and retrieves data using the provided DataHandler.

        Args:
            **kwargs: Additional keyword arguments to be passed to the getData method of the DataHandler.

        Returns:
            The response from the getData method if successful, False otherwise.
            
        """
        dh = self.provide_DataHandler()
        if not dh:
            self._logger("Could not provide data channel")
            return False
        
        response = dh.getData(**kwargs)

        if not response:
            return False
        else:
            return response
        
    def getAllSymbols(self):
        """
        Returns array of all symbols available for the user.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
	                            dictionary  SYMBOL_RECORD 

        Format of SYMBOL_RECORD:
            name	            type	    description
            ask	                float	    Ask price in base currency
            bid	                float	    Bid price in base currency
            categoryName	    string	    Category name
            contractSize	    integer     Size of 1 lot
            currency	        string	    Currency
            currencyPair	    boolean	    Indicates whether the symbol represents a currency pair
            currencyProfit	    string	    The currency of calculated profit
            description	        string	    Description
            expiration	        timestamp   Null if not applicable
            groupName	        string	    Symbol group name
            high	            float	    The highest price of the day in base currency
            initialMargin	    integer    	Initial margin for 1 lot order, used for profit/margin calculation
            instantMaxVolume    integer	    Maximum instant volume multiplied by 100 (in lots)
            leverage	        float	    Symbol leverage
            longOnly	        boolean	    Long only
            lotMax	            float	    Maximum size of trade
            lotMin	            float	    Minimum size of trade
            lotStep	            float	    A value of minimum step by which the size of trade can be changed (within lotMin - lotMax range)
            low	                float	    The lowest price of the day in base currency
            marginHedged	    integer	    Used for profit calculation
            marginHedgedStrong  boolean	    For margin calculation
            marginMaintenance   integer	    For margin calculation, null if not applicable
            marginMode	        integer	    For margin calculation
            percentage	        float	    Percentage
            pipsPrecision	    integer	    Number of symbol's pip decimal places
            precision	        integer	    Number of symbol's price decimal places
            profitMode	        integer	    For profit calculation
            quoteId     	    integer	    Source of price
            shortSelling	    boolean	    Indicates whether short selling is allowed on the instrument
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            starting	        timestamp	Null if not applicable
            stepRuleId	        integer	    Appropriate step rule ID from getStepRules  command response
            stopsLevel	        integer	    Minimal distance (in pips) from the current price where the stopLoss/takeProfit can be set
            swap_rollover3days  integer	    timestamp when additional swap is accounted for weekend
            swapEnable	        boolean	    Indicates whether swap value is added to position on end of day
            swapLong	        float	    Swap value for long positions in pips
            swapShort	        float	    Swap value for short positions in pips
            swapType	        integer	    Type of swap calculated
            symbol	            string	    Symbol name
            tickSize	        float	    Smallest possible price change, used for profit/margin calculation, null if not applicable
            tickValue	        float	    Value of smallest possible price change (in base currency), used for profit/margin calculation, null if not applicable
            time	            timestamp	Ask & bid tick time
            timeString	        string	    Time in String
            trailingEnabled	    boolean 	Indicates whether trailing stop (offset) is applicable to the instrument.
            type	            integer	    Instrument class number

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        Possible values of marginMode field:
            name	            value	    description
            Forex	            101	        Forex
            CFD leveraged	    102	        CFD leveraged
            CFD	                103	        CFD

        Possible values of profitMode field:
            name	            value	    description
            FOREX	            5	        FOREX
            CFD	                6	        CFD

        """
        return self._open_data_channel(command="AllSymbols")
    
    def getCalendar(self):
        """
        Returns calendar with market events.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
    	                        dictionary	CALENDAR_RECORD 

        Format of CALENDAR_RECORD:
            name	            type	    description
            country	            string	    Two letter country code
            current	            string	    Market value (current), empty before time of release of this value (time from "time" record)
            forecast	        string	    Forecasted value
            impact	            string	    Impact on market
            period	            string	    Information period
            previous	        string	    Value from previous information release
            time	            timestamp	Time, when the information will be released (in this time empty "current" value should be changed with exact released value)
            title           	String	    Name of the indicator for which values will be released

        Possible values of impact field:
            name	            value	    description
            low	                1	        low
            medium	            2	        medium
            high	            3	        high

        """
        return self._open_data_channel(command="Calendar")
    
    def getChartLastRequest(self, symbol: str, period: str, start: datetime=None):
        """
        Returns chart info, from start date to the current time. If the chosen period is greater than 1 minute, 
        the last candle returned by the API can change until the end of the period.
        the candle is being automatically updated every minute.

        Args:
            symbol (str): The symbol for which to retrieve the chart data.
            period (str): The period of the chart data. Must be one of the following: "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1".
            start (datetime, optional): The start time of the chart data. Default is 0 AD

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            digits	            integer	    Number of decimal places
            rateInfos	        dictionary	RATE_INFO_RECORD objects

        Format of RATE_INFO_RECORD:
            name	            type	    description
            close	            float	    Value of close price (shift from open price)
            ctm	                timestamp	Candle start time in CET / CEST time zone (see Daylight Saving Time, DST)
            ctmString	        string	    String representation of the 'ctm' field
            high	            float   	Highest value in the given period (shift from open price)
            low	                float	    Lowest value in the given period (shift from open price)
            open            	float	    Open price (in base currency * 10 to the power of digits)
            vol	                float	    Volume in lots

        """
        periods={'M1':1,'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440,'W1':10080,'MN1':43200}    

        if period not in periods:
            self._logger("Invalid period. Choose from: "+", ".join(periods))
            return False
        
        now=datetime.now()
        now_ux= datetime_to_unixtime(now)
        if periods[period] >= 1140:
            limit=datetime(1900,1,1)
        elif periods[period] >= 240:
            limit=now - relativedelta(years=13)
        elif periods[period] >= 30:
            limit=now - relativedelta(months=7)
        else:
            limit=now - relativedelta(months=1)
        limit_ux=datetime_to_unixtime(limit)
        
        if not start:
            start_ux=datetime_to_unixtime(datetime.min)
        else:
            start_ux=datetime_to_unixtime(start)

        if start_ux> now_ux:
            self._logger.error("Start time is greater than current time.")
            return False

        if start_ux< limit_ux:
            self._logger.warning("Start time is too far in the past for selected period "+period+". Setting start time to "+str(limit))
            start_ux=limit_ux

        return self._open_data_channel(command="ChartLastRequest", info=dict(period=periods[period], start=start_ux, symbol=symbol))

    def getChartRangeRequest(self, symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0):
        """
        Returns chart info with data between given start and end dates.

        Args:
            symbol (str): The symbol for which to retrieve the chart data.
            period (str): The time period of the chart data. Must be one of the following: "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1".
            start (datetime, optional): The start time of the chart data. Default 0 AD
            end (datetime, optional): The end time of the chart data. Default is now.
            ticks (int, optional): The number of ticks to retrieve. If set to 0, the start and end times are used. Defaults to 0.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            digits	            integer	    Number of decimal places
            rateInfos	        dictionary	RATE_INFO_RECORD

        Format of RATE_INFO_RECORD:
            name	            type	    description
            close	            float	    Value of close price (shift from open price)
            ctm	                timestamp	Candle start time in CET / CEST time zone (see Daylight Saving Time, DST)
            ctmString	        string	    String representation of the 'ctm' field
            high	            float   	Highest value in the given period (shift from open price)
            low	                float	    Lowest value in the given period (shift from open price)
            open            	float	    Open price (in base currency * 10 to the power of digits)
            vol	                float	    Volume in lots
        
        """
        periods={'M1':1,'M5':5,'M15':15,'M30':30,'H1':60,'H4':240,'D1':1440,'W1':10080,'MN1':43200}    

        if period not in periods:
            self._logger("Invalid period. Choose from: "+", ".join(periods))
            return False
        
        now=datetime.now()
        now_ux= datetime_to_unixtime(datetime.now())
        if periods[period] >= 1140:
            limit=datetime(1900,1,1)
        elif periods[period] >= 240:
            limit=now - relativedelta(years=13)
        elif periods[period] >= 30:
            limit=now - relativedelta(months=7)
        else:
            limit=now - relativedelta(months=1)
        limit_ux=datetime_to_unixtime(limit)

        if not start:
            start_ux=datetime_to_unixtime(datetime.min)
        else:
            start_ux=datetime_to_unixtime(start)

        if start_ux< limit_ux:
            self._logger.warning("Start time is too far in the past for selected period "+period+". Setting start time to "+str(limit))
            start_ux=limit_ux

        if start_ux> now_ux:
            self._logger.error("Start time is greater than current time.")
            return False

        if ticks == 0:
            if not end:
                end_ux=now_ux
            else:
                end_ux=datetime_to_unixtime(end)
                
            if end_ux> now_ux:
                self._logger.error("End time is greater than current time.")
                return False

            if start_ux>= end_ux:
                self._logger.error("Start time is greater or equal than end time.")
                return False
        else:
            self._logger.info("Ticks parameter is set. Ignoring end time.")

            reference = start

            if ticks < 0:
                if period in ["M1", "M5", "M15", "M30"]:
                    delta = calculate_timedelta(limit,reference, period='minutes')
                elif period in ["H1", "H4"]:
                    delta = calculate_timedelta(limit,reference, period='hours')
                elif period == "D1":
                    delta = calculate_timedelta(limit,reference, period='days')
                elif period == "W1":
                    delta = calculate_timedelta(limit,reference, period='weeks')
                else:
                    delta = calculate_timedelta(limit,reference,period='months')

                if delta < abs(ticks):
                    self._logger.warning("Ticks reach too far in the past for selected period "+period+". Setting tick to "+str(delta))
                    ticks = delta
            else:
                if period in ["M1", "M5", "M15", "M30"]:
                    delta = calculate_timedelta(reference, now, period='minutes')
                elif period in ["H1", "H4"]:
                    delta = calculate_timedelta(reference, now, period='hours')
                elif period == "D1":
                    delta = calculate_timedelta(reference, now, period='days')
                elif period == "W1":
                    delta = calculate_timedelta(reference, now, period='weeks')
                else:
                    delta = calculate_timedelta(reference, now, period='months')
                
                if delta < ticks:
                    self._logger.warning("Ticks reach too far in the future for selected period "+period+". Setting tick time to "+str(delta))
                    ticks = delta

        return self._open_data_channel(command="ChartRangeRequest", info=dict(end=end_ux, period=periods[period], start=start_ux, symbol=symbol, ticks=ticks))

    def getCommissionDef(self, symbol: str, volume: float):
        """
        Returns calculation of commission and rate of exchange. The value is calculated as expected value, and therefore might not be perfectly accurate.

        Args:
            symbol (str): The symbol for which to retrieve the commission definition.
            volume (float): The volume for which to retrieve the commission definition.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description        
            commission	        float	    calculated commission in account currency, could be null if not applicable
            rateOfExchange	    float	    rate of exchange between account currency and instrument base currency, could be null if not applicable

        """

        if volume < 0:
            self._logger.error("Volume must be greater than 0.")
            return False

        return self._open_data_channel(command="CommissionDef", symbol=symbol, volume=volume)
    
    def getCurrentUserData(self):
        """
        Returns information about account currency, and account leverage.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            companyUnit	        integer	    Unit the account is assigned to.
            currency	        string	    account currency
            group	            string	    group
            ibAccount	        boolean	    Indicates whether this account is an IB account.
            leverage	        integer	    This field should not be used. It is inactive and its value is always 1.
            leverageMultiplier	float	    The factor used for margin calculations. The actual value of leverage can be calculated by dividing this value by 100.
            spreadType	        string	    spreadType, null if not applicable
            trailingStop	    boolean	    Indicates whether this account is enabled to use trailing stop   

        """
        return self._open_data_channel(command="CurrentUserData")
    
    def getIbsHistory(self, start: datetime, end: datetime):
        """
        Retrieves the IBS (Internal Bar Strength) history data from the specified start time to the specified end time.

        Args:
            start (datetime): The start time of the data range.
            end (datetime): The end time of the data range.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
	                            dictionary  IB_RECORD 

        Format of IB_RECORD:
            name	            type	    description
            closePrice	        float	    IB close price or null if not allowed to view
            login	            string	    IB user login or null if not allowed to view
            nominal	            float	    IB nominal or null if not allowed to view
            openPrice	        float	    IB open price or null if not allowed to view
            side	            integer	    Operation code or null if not allowed to view
            surname	            string	    IB user surname or null if not allowed to view
            symbol	            string	    Symbol or null if not allowed to view
            timestamp	        timestamp	Time the record was created or null if not allowed to view
            volume	            float	    Volume in lots or null if not allowed to view

        Possible values of side field:
            name	            value   	description
            BUY	                0	        buy
            SELL	            1	        sell

        """
        start_ux=datetime_to_unixtime(start)
        end_ux=datetime_to_unixtime(end)

        if start_ux> end_ux:
            self._logger.error("Start time is greater than end time.")
            return False

        return self._open_data_channel(command="IbsHistory", end=end_ux, start=start_ux)
    
    def getMarginLevel(self):
        """
        Returns various account indicators.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            balance	            float	    balance in account currency
            credit	            float	    credit
            currency	        string	    user currency
            equity	            float	    sum of balance and all profits in account currency
            margin	            float	    margin requirements in account currency
            margin_free	        float	    free margin in account currency
            margin_level	    float	    margin level percentage


        """
        return self._open_data_channel(command="MarginLevel")
    
    def getMarginTrade(self, symbol: str, volume: float):
        """
        Returns expected margin for given instrument and volume. The value is calculated as expected margin value, and therefore might not be perfectly accurate.

        Args:
            symbol (str): The symbol for which to retrieve margin trade information.
            volume (float): The volume of the trade.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description        
            margin	            float	    calculated margin in account currency
              
        """
        if volume < 0:
            self._logger.error("Volume must be greater than 0.")
            return False

        return self._open_data_channel(command="MarginTrade", symbol=symbol, volume=volume)
    
    def getNews(self, start: datetime, end: datetime):
        """
        Retrieves news data from the XTB API within the specified time range.

        Args:
            start (datetime): The start time of the news data range.
            end (datetime): The end time of the news data range.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
	                            dictionary	NEWS_TOPIC_RECORD 

        Format of NEWS_TOPIC_RECORD:
            name	            type	    description
            body	            string      Body
            bodylen	            integer	    Body length
            key	                string      News key
            time	            timestamp   Time
            timeString	        string      Time string
            title	            string      News title
            
        """
        start_ux=datetime_to_unixtime(start)
        end_ux=datetime_to_unixtime(end)

        if start_ux> end_ux:
            self._logger.error("Start time is greater than end time.")
            return False

        return self._open_data_channel(command="News", end=end_ux, start=start_ux)
    
    def getProfitCalculation(self, symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int):
        """
        Calculates estimated profit for given deal data Should be used for calculator-like apps only.
        Profit for opened transactions should be taken from server, due to higher precision of server calculation.

        Args:
            symbol (str): The symbol of the trade.
            volume (float): The volume of the trade.
            openPrice (float): The opening price of the trade.
            closePrice (float): The closing price of the trade.
            cmd (int): The command type of the trade.

        Possible values of cmd field:
            name	            type	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            profit	            float	    Profit in account currency

        """
        cmds = [0, 1, 2, 3, 4, 5, 6, 7]

        if cmd not in cmds:
            self._logger.error("Invalid cmd. Choose from: "+", ".join(cmds))
            return False
        
        if volume < 0:
            self._logger.error("Volume must be greater than 0.")
            return False

        return self._open_data_channel(command="ProfitCalculation", closePrice=closePrice, cmd=cmd, openPrice=openPrice, symbol=symbol, volume=volume)
        
    def getServerTime(self):
        """
        Returns current time on trading server.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            time	            timestamp	Time
            timeString	        string      Time described in form set on server (local time of server)
        
        """
        return self._open_data_channel(command="ServerTime")
    
    def getStepRules(self):
        """
        Returns a list of step rules for DMAs.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
        	                    dictionary	STEP_RULE_RECORD

        Format of STEP_RULE_RECORD:
            name	            type	    description
            id	                integer	    Step rule ID
            name	            string      Step rule name
            steps	            dictionary	STEP_RECORD

        Format of STEP_RECORD:
            name	            type	    description
            fromValue	        float	    Lower border of the volume range
            step	            float	    lotStep value in the given volume range

        """
        return self._open_data_channel(command="StepRules")

    def getSymbol(self, symbol: str):
        """
        Returns information about symbol available for the user.

        Args:
            symbol (str): The symbol to retrieve information for.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            ask	                float	    Ask price in base currency
            bid	                float	    Bid price in base currency
            categoryName	    string	    Category name
            contractSize	    integer     Size of 1 lot
            currency	        string	    Currency
            currencyPair	    boolean	    Indicates whether the symbol represents a currency pair
            currencyProfit	    string	    The currency of calculated profit
            description	        string	    Description
            expiration	        timestamp	Null if not applicable
            groupName	        string	    Symbol group name
            high	            float	    The highest price of the day in base currency
            initialMargin	    integer    	Initial margin for 1 lot order, used for profit/margin calculation
            instantMaxVolume    integer	    Maximum instant volume multiplied by 100 (in lots)
            leverage	        float	    Symbol leverage
            longOnly	        boolean	    Long only
            lotMax	            float	    Maximum size of trade
            lotMin	            float	    Minimum size of trade
            lotStep	            float	    A value of minimum step by which the size of trade can be changed (within lotMin - lotMax range)
            low	                float	    The lowest price of the day in base currency
            marginHedged	    integer	    Used for profit calculation
            marginHedgedStrong  boolean	    For margin calculation
            marginMaintenance   integer	    For margin calculation, null if not applicable
            marginMode	        integer	    For margin calculation
            percentage	        float	    Percentage
            pipsPrecision	    integer	    Number of symbol's pip decimal places
            precision	        integer	    Number of symbol's price decimal places
            profitMode	        integer	    For profit calculation
            quoteId     	    integer	    Source of price
            shortSelling	    boolean	    Indicates whether short selling is allowed on the instrument
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            starting	        timestamp	Null if not applicable
            stepRuleId	        integer	    Appropriate step rule ID from getStepRules  command response
            stopsLevel	        integer	    Minimal distance (in pips) from the current price where the stopLoss/takeProfit can be set
            swap_rollover3days	integer	    timestamp when additional swap is accounted for weekend
            swapEnable	        boolean	    Indicates whether swap value is added to position on end of day
            swapLong	        float	    Swap value for long positions in pips
            swapShort	        float	    Swap value for short positions in pips
            swapType	        integer	    Type of swap calculated
            symbol	            string	    Symbol name
            tickSize	        float	    Smallest possible price change, used for profit/margin calculation, null if not applicable
            tickValue	        float	    Value of smallest possible price change (in base currency), used for profit/margin calculation, null if not applicable
            time	            timestamp	Ask & bid tick time
            timeString	        string	    Time in String
            trailingEnabled	    boolean 	Indicates whether trailing stop (offset) is applicable to the instrument.
            type	            integer	    Instrument class number

        Possible values of quoteId field:
            name	            value	    description
            fixed	            1	        fixed
            float	            2	        float
            depth	            3	        depth
            cross	            4	        cross

        Possible values of marginMode field:
            name	            value	    description
            Forex	            101	        Forex
            CFD leveraged	    102	        CFD leveraged
            CFD	                103	        CFD

        Possible values of profitMode field:
            name	            value	    description
            FOREX	            5	        FOREX
            CFD	                6	        CFD

        """
        return self._open_data_channel(command="Symbol", symbol=symbol)
    
    def getTickPrices(self, symbols: list, time: datetime, level: int=-1):
        """
        Retrieves tick prices for the specified symbols at the given time.

        Args:
            symbols (list): A list of symbols for which tick prices are to be retrieved.
            time (datetime): The timestamp at which tick prices are to be retrieved.
            level (int, optional): The level of tick prices to retrieve. Defaults to -1.

        Possible values of level field:
            name	            type	    description
                                -1	        all available levels
                                 0	        base level bid and ask price for instrument
                                >0	        specified level      

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            quotations  	    dictionary	TICK_RECORD 

        Format of TICK_RECORD:
            name	            type	    description
            ask	                float	    Ask price in base currency
            askVolume	        int	        Number of available lots to buy at given price or null if not applicable
            bid	                float	    Bid price in base currency
            bidVolume	        int	        Number of available lots to buy at given price or null if not applicable
            high	            float	    The highest price of the day in base currency
            level	            int	        Price level
            low	                float	    The lowest price of the day in base currency
            spreadRaw	        float	    The difference between raw ask and bid prices
            spreadTable	        float	    Spread representation
            symbol	            string	    Symbol
            timestamp	        timestamp	Timestamp
            
        """
        levels = [-1, 0]

        if level not in levels or level > 0:
            self._logger.error("Invalid level. Choose from: "+", ".join(levels))
            return False
        
        if not all(isinstance(item, str) for item in symbols):
            self._logger.error("Invalid symbols. All symbols must be strings.")
            return False
        
        timestamp = datetime_to_unixtime(time)

        return self._open_data_channel(command="TickPrices", level=level, symbols=symbols, timestamp=timestamp)
    
    def getTradeRecords(self, orders: list):
        """
        Returns array of trades listed in orders argument.

        Args:
            orders (list): A list of order IDs.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
	                            dictionary	TRADE_RECORD
        
        Format of TRADE_RECORD:
            name	            type	    description
            close_price	        float       Close price in base currency
            close_time	        timestamp	Null if order is not closed
            close_timeString	string      Null if order is not closed
            closed	            boolean	    Closed
            cmd	                integer	    Operation code
            comment	            string      Comment
            commission	        float       Commission in account currency, null if not applicable
            customComment	    string      The value the customer may provide in order to retrieve it later.
            digits	            integer	    Number of decimal places
            expiration	        timestamp	Null if order is not closed
            expirationString	string      Null if order is not closed
            margin_rate     	float       Margin rate
            offset	            integer	    Trailing offset
            open_price	        float       Open price in base currency
            open_time	        timestamp	Open time
            open_timeString	    string      Open time string
            order	            integer	    Order number for opened transaction
            order2	            integer	    Order number for closed transaction
            position	        integer	    Order number common both for opened and closed transaction
            profit	            float       Profit in account currency
            sl	                float       Zero if stop loss is not set (in base currency)
            storage	            float       Order swaps in account currency
            symbol	            string      Symbol name or null for deposit/withdrawal operations
            timestamp	        timestamp	Timestamp
            tp	                float       Zero if take profit is not set (in base currency)
            volume	            float       Volume in lots

        Possible values of cmd field:
            name	            value	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

            
        """
        if not all(isinstance(item, int) for item in orders):
            self._logger.error("Invalid order. All orders must be integers.")
            return False

        return self._open_data_channel(command="TradeRecords", orders=orders)
    
    def getTrades(self, openedOnly: bool):
        """
        Returns array of user's trades.

        Parameters:
        - openedOnly (bool): If True, only retrieves opened trades. If False, retrieves all trades.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
                                dictionary	TRADE_RECORD

        Format of TRADE_RECORD:
            name	            type	    description
            close_price	        float       Close price in base currency
            close_time	        timestamp	Null if order is not closed
            close_timeString	string      Null if order is not closed
            closed	            boolean	    Closed
            cmd	                integer	    Operation code
            comment	            string      Comment
            commission	        float       Commission in account currency, null if not applicable
            customComment	    string      The value the customer may provide in order to retrieve it later.
            digits	            integer	    Number of decimal places
            expiration	        timestamp	Null if order is not closed
            expirationString	string      Null if order is not closed
            margin_rate     	float       Margin rate
            offset	            integer	    Trailing offset
            open_price	        float       Open price in base currency
            open_time	        timestamp	Open time
            open_timeString	    string      Open time string
            order	            integer	    Order number for opened transaction
            order2	            integer	    Order number for closed transaction
            position	        integer	    Order number common both for opened and closed transaction
            profit	            float       Profit in account currency
            sl	                float       Zero if stop loss is not set (in base currency)
            storage	            float       Order swaps in account currency
            symbol	            string      Symbol name or null for deposit/withdrawal operations
            timestamp	        timestamp	Timestamp
            tp	                float       Zero if take profit is not set (in base currency)
            volume	            float       Volume in lots

        Possible values of cmd field:
            name	            value	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        """
        return self._open_data_channel(command="Trades", openedOnly=openedOnly)
    
    def getTradeHistory(self, start: datetime, end: datetime):
        """
        Returns array of user's trades which were closed within specified period of time.

        Args:
            start (datetime): The start timestamp.
            end (datetime): The end timestamp.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
                                dictionary	TRADE_RECORD

        Format of TRADE_RECORD:
            name	            type	    description
            close_price	        float       Close price in base currency
            close_time	        timestamp	Null if order is not closed
            close_timeString	string      Null if order is not closed
            closed	            boolean	    Closed
            cmd	                integer	    Operation code
            comment	            string      Comment
            commission	        float       Commission in account currency, null if not applicable
            customComment	    string      The value the customer may provide in order to retrieve it later.
            digits	            integer	    Number of decimal places
            expiration	        timestamp	Null if order is not closed
            expirationString	string      Null if order is not closed
            margin_rate     	float       Margin rate
            offset	            integer	    Trailing offset
            open_price	        float       Open price in base currency
            open_time	        timestamp	Open time
            open_timeString	    string      Open time string
            order	            integer	    Order number for opened transaction
            order2	            integer	    Order number for closed transaction
            position	        integer	    Order number common both for opened and closed transaction
            profit	            float       Profit in account currency
            sl	                float       Zero if stop loss is not set (in base currency)
            storage	            float       Order swaps in account currency
            symbol	            string      Symbol name or null for deposit/withdrawal operations
            timestamp	        timestamp	Timestamp
            tp	                float       Zero if take profit is not set (in base currency)
            volume	            float       Volume in lots

        Possible values of cmd field:
            name	            value	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        """
        start_ux= datetime_to_unixtime(start)
        end_ux= datetime_to_unixtime(end)

        if start_ux> end_ux:
            self._logger.error("Start time is greater than end time.")
            return False

        return self._open_data_channel(command="TradeHistory", start=start_ux, end=end_ux)

    def getTradingHours(self, symbols: list):
        """
        Returns quotes and trading times.

        Args:
            symbols (list): A list of symbols for which to retrieve trading hours.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            quotes	            dictionary	QUOTES_RECORD 
            symbol	            string      Symbol
            trading	            dictionary	TRADING_RECORD 

        Format of QUOTES_RECORD:
            name	            type	    description
            day	                integer	    Day of week
            fromT	            timestamp	Start time in ms from 00:00 CET / CEST time zone (see Daylight Saving Time, DST)
            toT	                timestamp	End time in ms from 00:00 CET / CEST time zone (see Daylight Saving Time, DST)

        Format of TRADING_RECORD:
            name	            type	    description
            day	                integer	    Day of week
            fromT	            timestamp	Start time in ms from 00:00 CET / CEST time zone (see Daylight Saving Time, DST)
            toT             	timestamp	End time in ms from 00:00 CET / CEST time zone (see Daylight Saving Time, DST)

        Possible values of day field:
            name	            type	    description
                                1	        Monday
                                2	        Tuesday
                                3	        Wednesday
                                4	        Thursday
                                5	        Friday
                                6	        Saturday
                                7	        Sunday
            
        """
        if not all(isinstance(item, str) for item in symbols):
            self._logger.error("Invalid symbols. All symbols must be strings.")
            return False

        return self._open_data_channel(command="TradingHours", symbols=symbols)

    def getVersion(self):
        """
        Returns the current API version.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            version	            string	    API versionversion	String	current API version      

        """
        return self._open_data_channel(command="Version")
    
    def tradeTransaction(self, cmd: int, customComment: str, expiration: datetime, offset: int, order: int, price: float, sl: float, symbol: str, tp: float, type: int, volume: float):
        """
        Executes a trade transaction.

        Args:
            cmd (int): Operation code
            customComment (str): The value the customer may provide in order to retrieve it later.
            expiration (datetime): Pending order expiration time
            offset (int): Trailing offset
            order (int): 0 or position number for closing/modifications
            price (float): Trade price
            sl (float): Stop loss
            symbol (str): Trade symbol
            tp (float): Take profit
            type (int): Trade transaction type
            volume (float): Trade volume

        Possible values of cmd field:
            name	            type	    description
            BUY	                0	        buy
            SELL	            1	        sell
            BUY_LIMIT	        2	        buy limit
            SELL_LIMIT	        3	        sell limit
            BUY_STOP	        4	        buy stop
            SELL_STOP	        5	        sell stop
            BALANCE	            6	        Read only. Used in getTradesHistory  for manager's deposit/withdrawal operations (profit>0 for deposit, profit<0 for withdrawal).
            CREDIT	            7	        Read only

        Possible values of type field:
            name	            type	    description
            OPEN	            0	        order open, used for opening orders
            PENDING	            1	        order pending, only used in the streaming getTrades  command
            CLOSE	            2	        order close
            MODIFY	            3	        order modify, only used in the tradeTransaction  command
            DELETE	            4	        order delete, only used in the tradeTransaction  command

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            order	            integer	    order

        """
        cmds = [0, 1, 2, 3, 4, 5, 6, 7]
        types = [0, 1, 2, 3, 4]

        if cmd not in cmds:
            self._logger.error("Invalid cmd. Choose from: "+", ".join(cmds))
            return False
        
        if type not in types:
            self._logger.error("Invalid type. Choose from: "+", ".join(types))
            return False
        
        if expiration < datetime.datetime.now():
            self._logger.error("Expiration time is in the past.")
            return False
        
        if volume < 0:
            self._logger.error("Volume must be greater than 0.")
            return False

        expiration_ux= datetime_to_unixtime(expiration)

        return self._open_data_channel(command="tradeTransaction", tradeTransInf=dict(cmd=cmd, customCommand=customComment, expiration=expiration_ux, offset=offset, order=order, price=price, sl=sl, symbol=symbol, tp=tp, type=type, volume=volume))
    
    def tradeTransactionStatus(self, order: int):
        """
        Returns current transaction status.

        Parameters:
        order (int): The order ID for which to retrieve the transaction status.

        Returns:
            Dictionary: A Dictionary containing the following fields:
            name	            type	    description
            ask	                float	    Price in base currency
            bid	                float	    Price in base currency
            customComment	    string	    The value the customer may provide in order to retrieve it later.
            message	            string	    Can be null
            order	            integer	    Unique order number
            requestStatus	    integer	    Request status code, described below

        Possible values of requestStatus field:
            name	            type	    description
            ERROR	            0	        error
            PENDING	            1	        pending
            ACCEPTED	        3	        The transaction has been executed successfully
            REJECTED	        4       	The transaction has been rejected

        """
        return self._open_data_channel(command="tradeTransactionStatus", order=order)
