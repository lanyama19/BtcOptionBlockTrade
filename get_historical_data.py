from fetch_data import call_api
import datetime
import asyncio
import pandas as pd



start_date = "2021-11-08"
end_date = "2024-11-09"
start_ts = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp()*1000)
end_ts =  int(datetime.datetime.strptime(end_date , "%Y-%m-%d").timestamp()*1000)


msg = \
    {
        "jsonrpc": "2.0",
        "id": 833,
        "method": "public/get_tradingview_chart_data",
        "params": {
            "instrument_name": "BTC-PERPETUAL",
            "start_timestamp": start_ts,
            "end_timestamp": end_ts,
            "resolution": "1D"
        }
    }

json_data = asyncio.run(call_api(msg))['result']
price_df = pd.DataFrame(json_data)
price_df['date_time'] = pd.to_datetime(price_df ['ticks'], unit='ms')
price_df.to_csv("price_df_1d.csv", index=False)


## get DVOL data
# msg = \
# {
#   "jsonrpc" : "2.0",
#   "id" : 833,
#   "method" : "public/get_volatility_index_data",
#   "params" : {
#     "currency" : "BTC",
#     "start_timestamp" : start_ts,
#     "end_timestamp" : end_ts,
#     "resolution" : "1D"
#   }
# }
#
# json_data = asyncio.run(call_api(msg))['result']['data']
# dvol_df = pd.DataFrame(json_data)
# dvol_df.columns = ["ticks", "open", "high","low","close"]
# dvol_df['date_time'] = pd.to_datetime(dvol_df['ticks'], unit='ms')
# dvol_df.to_csv("dvol_df.csv", index=False)
#
# msg2 = \
# {
#   "jsonrpc" : "2.0",
#   "id" : 833,
#   "method" : "public/get_volatility_index_data",
#   "params" : {
#     "currency" : "BTC",
#     "start_timestamp" : start_ts,
#     "end_timestamp" : 1644796800000,
#     "resolution" : "1D"
#   }
# }
#
# json_data2 = asyncio.run(call_api(msg2))['result']['data']
# dvol_df2 = pd.DataFrame(json_data2)
# dvol_df2.columns = ["ticks", "open", "high","low","close"]
# dvol_df2['date_time'] = pd.to_datetime(dvol_df2['ticks'], unit='ms')
# dvol_df2.to_csv("dvol_df2.csv", index=False)

## compute realized vols
## get block trade data