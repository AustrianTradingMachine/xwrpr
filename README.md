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

<br/>

**Streaming Commands**
===================
* 

Example
-------

```python





import pandas as pd
import pandas_ta as ta

df = pd.DataFrame() # Empty DataFrame

# Load data
df = pd.read_csv("path/to/symbol.csv", sep=",")
# OR if you have yfinance installed
df = df.ta.ticker("aapl")

# VWAP requires the DataFrame index to be a DatetimeIndex.
# Replace "datetime" with the appropriate column from your DataFrame
df.set_index(pd.DatetimeIndex(df["datetime"]), inplace=True)

# Calculate Returns and append to the df DataFrame
df.ta.log_return(cumulative=True, append=True)
df.ta.percent_return(cumulative=True, append=True)

# New Columns with results
df.columns

# Take a peek
df.tail()

# vv Continue Post Processing vv
```

<br/>

<br />

# **Sources**
[XTB](https://www.xtb.com/) | [xAPI Protocol Documentation](http://developers.xstore.pro/documentation/) 

<br/>
