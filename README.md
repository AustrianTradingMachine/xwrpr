XTBpy - A wrapper for the API of XTB (https://www.xtb.com)
=================

<br/>

# **Table of contents**

<!--ts-->
* [Features](#features)
* [Installation](#installation)
* [Documentation](#documentation)
* [Data Commands](#data_commands)
    * [Commands](#commands)
    * [Example](#example)
* [Streaming Commands](#streaming_commands)
     * [Commands](#commands)
     * [Example](#example)
* [Data Commands](#data_commands)
* [Sources](#sources)


<br/>

# **Features**

* 


<br/>

**Installation**
===================
<br/>

**Documentation**
===================

You find the official documentation of the XTB API under: [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/) 

**Data Commands**
===================
XTBpy includes all Data commands, exept
* ping
</n>
this command is automatically executed by XTBpy

Commands
--------
In the following all available data commands are listed.

* getAllSymbols()
* getCalendar()
* getChartLastRequest(symbol: str, period: str, start: datetime=None)
* getChartRangeRequest(symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0)
* getCommissionDef(symbol: str, volume: float)
* getCurrentUserData()
* getIbsHistory(start: datetime, end: datetime)
* getMarginLevel()
* getMarginTrade(symbol: str, volume: float)
* getNews(start: datetime, end: datetime)
* getProfitCalculation(symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int)
* getServerTime()
* getStepRules()
* getSymbol(symbol: str)
* getTickPrices(symbols: list, time: datetime, level: int=-1)
* getTradeRecords(orders: list)
* getTrades(openedOnly: bool)
* getTradeHistory(start: datetime, end: datetime)
* getTradingHours(symbols: list)
* getVersion()
* tradeTransaction(cmd: int, customComment: str, expiration: datetime, offset: int, order: int, price: float, sl: float, symbol: str, tp: float, type: int, volume: float)
* tradeTransactionStatus(order: int)

The return will always be a dictionary with the key-value pairs of the "returnData" key of the JSON response file.
You will find a full documentation of all commands here: [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/)

Example
-------
the following example will show how to stream data with XTBpy.
You will find this example also in tests/test_get_symbol.py

```python
import XTB
from pathlib import Path

# Setting DEMO to True will use the demo account
DEMO=False

# just example how to generate alogger. Feel free to use your own logger
logger=XTB.generate_logger(name="TEST_get_symbol",path=Path('~/Logger/XTBpy').expanduser())

# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# getting data for the symbols
symbol=XTBData.getSymbol(symbol='ETHEREUM')

print(symbol)

# Close Wrapper
XTBData.delete()
```
<br/>

**Streaming Commands**
===================
XTBpy includes all Streaming commands, exept
* ping
* KeepAlive
</n>
this two commands are automatically executed by XTBpy

Commands
--------
In the following all available streaming commands are listed.
In contrast to the officiall streaming commands which ar called get_Command_,
the streaming commands in XTBpy are called stream_Command_.
This was necessary becous of double Naming from the official API.

*```python streamBalance()```
*``` streamCandles(symbol: str)```
* ```streamNews()```
* ```streamProfits()```
* ```streamTickPrices(symbol: str, minArrivalTime: int, maxLevel: int=1)```
*``` streamTrades()```
* ```streamTradeStatus()```

The return will be a dictionary, containing the following elements:
   * df (pandas.DataFrame): The DataFrame to store the streamed data.
   * lock (threading.Lock): A lock object for synchronization of DataFrame Access.
   * thread (Thread): Starting the Thread will terminate the stream

The header of the dataframe will contain all keys of the "data" key of the JSON response file.
The streamed values will be in the row of the dataframe.
You will find a full documentation of all commands here: [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/)
For pandas DataFrame doku see here: [Pandas](https://pandas.pydata.org/) 

Example
-------
the following example will show how to stream data with XTBpy.
You will find this example also in tests/test_stream_ticker.py

```python
import XTB
from pathlib import Path
import time
from datetime import datetime, timedelta

# Setting DEMO to True will use the demo account
DEMO=False

# just example how to generate alogger. Feel free to use your own logger
logger=XTB.generate_logger(name="TEST_stream_ticker",path=Path('~/Logger/XTBpy').expanduser())

# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# Streaming data an reading the df
exchange=XTBData.streamTickPrices(symbol='ETHEREUM', minArrivalTime=0, maxLevel=1)

# Streaming data an reading the df
later = datetime.now() + timedelta(seconds=60*1)

while datetime.now() < later:
    exchange['lock'].acquire(blocking=True)
    if not exchange['df'].empty:
        print(exchange['df'].to_string(index=False, header=False))
        exchange['df'] = exchange['df'].iloc[0:0]
    exchange['lock'].release()
    time.sleep(1)

exchange['thread'].start()

# Close Wrapper
XTBData.delete()

```

<br/>

<br />

# **Sources**
[XTB](https://www.xtb.com/) | [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/) | [Pandas](https://pandas.pydata.org/) 

<br/>
