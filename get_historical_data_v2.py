import datetime
import asyncio
import pandas as pd
from fetch_data import call_api
import numpy as np

def fetch_btc_data(start_date: str, end_date: str, instrument_name: str = "BTC-PERPETUAL",
                   resolution: str = "5") -> pd.DataFrame:
    """
    分段请求API数据并将所有数据合并为一个DataFrame

    参数:
    start_date (str): 开始日期, 格式为 YYYY-MM-DD
    end_date (str): 结束日期, 格式为 YYYY-MM-DD
    instrument_name (str): 交易工具名称, 默认为 "BTC-PERPETUAL"
    resolution (str): 分时间隔隔, 默认为 "5"

    返回:
    pd.DataFrame: 合并的DataFrame
    """

    # 将开始日期和结束日期转换为毫秒时间戳
    start_ts = int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

    # 每次请求的最大距离为一定值 (5分钟 * 5000条)
    interval_ms = 5 * 60 * 1000 * 5000  # 5 分钟 * 60 秒 * 1000 毫秒 * 5000

    all_dataframes = []  # 用于存储每个时间段的DataFrame

    # 根据每次请求的限制分段请求
    current_start_ts = start_ts
    while current_start_ts < end_ts:
        current_end_ts = min(current_start_ts + interval_ms, end_ts)
        msg = {
            "jsonrpc": "2.0",
            "id": 833,
            "method": "public/get_tradingview_chart_data",
            "params": {
                "instrument_name": instrument_name,
                "start_timestamp": current_start_ts,
                "end_timestamp": current_end_ts,
                "resolution": resolution
            }
        }

        try:
            # 请求API数据
            json_data = asyncio.run(call_api(msg))['result']

            # 将数据转为DataFrame
            price_df = pd.DataFrame(json_data)

            if not price_df.empty:
                # 添加日期时间字段
                price_df['date_time'] = pd.to_datetime(price_df['ticks'], unit='ms')
                all_dataframes.append(price_df)  # 将该段数据添加到总集中
        except Exception as e:
            print(f"Error fetching data from {current_start_ts} to {current_end_ts}: {e}")

        # 进入下一段请求
        current_start_ts = current_end_ts

    if all_dataframes:
        # \5408并所有数据为一个DataFrame
        final_df = pd.concat(all_dataframes, ignore_index=True)
    else:
        final_df = pd.DataFrame()  # 如果没有数据则返回一个空的DataFrame

    return final_df


def calculate_realized_volatility(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    计算每日的已实现波动率

    参数:
    price_df (pd.DataFrame): 包含价格数据的DataFrame

    返回:
    pd.DataFrame: 包含每日已实现波动率的DataFrame
    """
    if 'close' not in price_df.columns:
        raise ValueError("DataFrame 必须包含 'close' 列")

    # 确保 'date_time' 列是 datetime 格式
    price_df['date_time'] = pd.to_datetime(price_df['date_time'],
                                           errors='coerce')  # 将 date_time 转换为datetime格式，并将无效数据转换为NaT
    if price_df['date_time'].isnull().any():
        raise ValueError("`date_time` 列中包含无效的时间格式，请检查数据是否包含NaT或无效的时间戳。")

    # 提取日期并计算对数收益率
    price_df['date'] = price_df['date_time'].dt.date  # 提取日期部分
    price_df['log_return'] = np.log(price_df['close'] / price_df['close'].shift(1))  # 计算对数收益率

    # 计算每日的已实现波动率
    daily_volatility = price_df.groupby('date')['log_return'].apply(lambda x: np.sqrt(np.sum(x ** 2)))

    # 重置索引并重命名列
    volatility_df = daily_volatility.reset_index()
    volatility_df.columns = ['date', 'realized_volatility']

    return volatility_df


# 例子调用
if __name__ == "__main__":
    start_date = "2021-11-08"
    end_date = "2024-11-09"
    df = fetch_btc_data(start_date, end_date)
    df.to_csv("price_df_frq.csv", index=False)  # 将数据保存为文件

    # 读取本地的 price_df_5min.csv 文件
    # price_df = pd.read_csv('price_df_1D.csv')
    # 计算每日的已实现波动率
    # volatility_df = calculate_realized_volatility(price_df)
    # 将每日的已实现波动率保存为CSV文件
    # volatility_df.to_csv('daily_realized_volatility.csv', index=False)
    # jupyter notebook --notebook-dir= "E:/py_projects"