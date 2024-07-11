XTBpy - A wrapper for the API of XTB
=================

<br/>

# **Table of contents**

<!--ts-->
* [Features](#features)
* [XTB-resources](#xtb-resources)
* [Installation](#installation)
* [Data](#data)
    * [Commands](#commands)
    * [Example](#example)
* [Streaming](#streaming)
     * [Commands](#streaming-commands)
     * [Example](#example)
* [Contributing](#contributing)
* [License](#license)
* [Sources](#sources)
<!--te-->

<br/>

# **Features**

 * **Comprehensive Data Commands**: Supports all data commands of the XTB API.
* **Automatic Background Tasks**: Ping command automatically executed in the background.
* **User-Friendly Installation**: Easy installation via pip.
* **Secure Configuration**: User credentials stored in `.ini` file with access restrictions.
* **Time Zone Handling**: Automatic conversion of local time to UTC-UX timestamps.
* **Streaming Support**: Includes all streaming commands of the XTB API.
* **Dynamic DataFrames**: Streaming data managed in dynamically updated Pandas DataFrames.
* **Thread-Safe Access**: Synchronization of DataFrame access using threading locks.
* **Examples**: Sample code provided for both data retrieval and streaming.
* **Documentation**: Full documentation of all API data and streaming commands.


## **Caution**
Please consider that XTBpy is still in Alpha stage and needs more development to run stable and reliant.

<br/>

# **XTB resources**
* [XTB](https://www.xtb.com/)
* [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/)
* [xAPIConnector](http://developers.xstore.pro/public/files/xAPI25-XTB-python.zip)



# **Installation**

You can install the XTB API Python Wrapper via pip:
```bash
pip install XTBpy
```

* After installation a file ```.XTBpy/user.ini``` is created in your home directory.
* To get accesd to your XTB account via XTBpy, you must enter your login data in ```user.ini```.
* Please ensure that no other person has access to your data.

<br/>

# **Data**

XTBpy includes all Data commands of the XTB API exept:
   * ```ping```
</n>
This command is automatically executed in the background.

## **Commands**

* All available data commands are listed below with their Input arguments and format.

   * ```getAllSymbols()```
   * ```getCalendar()```
   * ```getChartLastRequest(symbol: str, period: str, start: datetime=None)```
   * ```getChartRangeRequest(symbol: str, period: str, start: datetime=None, end: datetime=None, ticks: int=0)```
   * ```getCommissionDef(symbol: str, volume: float)```
   * ```getCurrentUserData()```
   * ```getIbsHistory(start: datetime, end: datetime)```
   * ```getMarginLevel()```
   * ```getMarginTrade(symbol: str, volume: float)```
   * ```getNews(start: datetime, end: datetime)```
   * ```getProfitCalculation(symbol: str, volume: float, openPrice: float, closePrice: float, cmd: int)```
   * ```getServerTime()```
   * ```getStepRules()```
   * ```getSymbol(symbol: str)```
   * ```getTickPrices(symbols: list, time: datetime, level: int=-1)```
   * ```getTradeRecords(orders: list)```
   * ```getTrades(openedOnly: bool)```
   * ```getTradeHistory(start: datetime, end: datetime)```
   * ```getTradingHours(symbols: list)```
   * ```getVersion()```
   * ```tradeTransaction(cmd: int, customComment: str, expiration: datetime, offset: int, order: int, price: float, sl: float, symbol: str, tp: float, type: int, volume: float)```
   * ```tradeTransactionStatus(order: int)```

* The return value will always be a ```dict``` (dictionary) with the key-value pairs of the "returnData" key of the API JSON response file.
* You will find a full documentation of all API data commands here: [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/)

### **Differences**
For simplicity certain argument formats differ from the original API commands:

#### Datetime
When commands have a time value as an argument, the time must be entered as a ```datetime``` object.
Datetime objects, which are defined in your operating system's time zone, will be automatically converted to a UTC-UX timestamp which is required by the XTB API.

#### Period
When commands include a period value as an argument, it must be passed as an item of the following string.
```"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"```

## **Example**

The following example will show how to retrieve data with XTBpy.
You will find this example also in tests/test_get_symbol.py.

```python
import XTB

# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# getting data for the symbols
symbol=XTBData.getSymbol(symbol='ETHEREUM')

print(symbol)

```
<br/>

# **Streaming**

XTBpy includes all Streaming commands of the XTB API exept:
   * ```ping```
   * ```getKeepAlive```
</n>
This two commands are automatically executed in the background.

## **Commands**

Unlike the official API streaming commands like get*Command*,
the streaming commands in XTBpy are called stream*Command*.
This was necessary due to double naming of certain commands by the official API.

*All available streaming commands are listed below with their Input arguments and format.

   * ```streamBalance()```
   * ```streamCandles(symbol: str)```
   * ```streamNews()```
   * ```streamProfits()```
   * ```streamTickPrices(symbol: str, minArrivalTime: int, maxLevel: int=1)```
   * ```streamTrades()```
   * ```streamTradeStatus()```

* The return value will be a dictionary, containing the following elements:
   * ```df``` (pandas.DataFrame): A DataFrame that contains the stream data.
   * ```lock``` (threading.Lock): A lock object for synchronization of the DataFrame access.
   * ```thread``` (Thread): Starting the thread will terminate the stream.

* The header of the dataframe will contain all keys of the "data" key of the JSON response file.
* The streamed values will be in the row of the DataFrame. The Dataframe will be dynamically updated by XTBpy and has a maximum of 1000 rows. Older values will be deleted from the DataFrame. The newest values can be found at the bottom row.
* Please see the example below to find out how to access the values in the DataFrame.
* You will find a full documentation of all API stream commands here: [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/)
* The Pandas DataFrame documentation can be found here: [Pandas](https://pandas.pydata.org/) 

## **Example**

The following example will show how to stream data with XTBpy.
You will find this example also in tests/test_stream_ticker.py

```python
import XTB

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

# **Contributing**

Improvements to the XTBpy project are welcome, whether it's a request, a suggestion, or a bug report. Just reach out!

<br/>

# **License**

XTBpy uses the GNU GENERAL PUBLIC LICENSE Version 3

You should have received a copy of the GNU General Public License
    along with this program.  If not, see [GNU GPL 3](https://www.gnu.org/licenses/
<br/>

# **Sources**
[XTB](https://www.xtb.com/) | [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/) | [xAPIConnector](http://developers.xstore.pro/public/files/xAPI25-XTB-python.zip) | [Pandas](https://pandas.pydata.org/) | [GNU GPL 3](https://www.gnu.org/licenses/)

<br/>
