XTBpy - A wrapper for the API of XTB (https://www.xtb.com)
=================

<br/>

# **Table of contents**

<!--ts-->
* [Features](#features)
* [Installation](#installation)
* [Data Commands](#data_commands)
* [Streaming Commands](#streaming_commands)
* [Data Commands](#data_commands)
* [Sources](#sources)


<br/>

# **Features**

* 


<br/>

**Installation**
===================

<br/>

**Data Commands**
===================

Example
-------
```python
import XTB
from pathlib import Path

# Setting DEMO to True will use the demo account
DEMO=False

# just example how to generate alogger. Feel free to use your own logger
logger=XTB.generate_logger(name="TEST_get_symbol",path=Path('~/Logger/XTBpy').expanduser())

# Creating Wrapper
XTBData=XTB.Wrapper(demo=DEMO, logger=logger)

# getting all symbols
# could take some time
symbol=XTBData.getSymbol(symbol='ETHEREUM')

print(symbol)

# Close Wrapper
XTBData.delete()
```
<br/>

**Streaming Commands**
===================
* 

Example
-------

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
[XTB](https://www.xtb.com/) | [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/) 

<br/>
