import asyncio
import websockets
import json

# 替换为您的 Deribit API 凭据
CLIENT_ID = 'XXXXX'
CLIENT_SECRET = 'YYYYYYYY'


# 构建身份验证消息
def create_auth_message():
    return {
        "jsonrpc": "2.0",
        "id": 9929,
        "method": "public/auth",
        "params": {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    }


# 构建获取大宗交易信息的消息
def create_block_trade_message(trade_id):
    return {
        "jsonrpc": "2.0",
        "id": 9930,
        "method": "private/get_block_trade",
        "params": {
            "id": trade_id
        }
    }

def create_get_last_block_trades_message(currency, count=None):
    """
    创建用于获取指定货币最近大宗交易的消息。
    """
    if count is None:
        count = 1  # 默认获取最近的 10 笔大宗交易

    return {
        "jsonrpc": "2.0",
        "method": "private/get_last_block_trades_by_currency",
        "params": {
            "currency": currency,
            "count": count
        }
    }


# 发送消息并接收响应
async def send_message(websocket, message):
    await websocket.send(json.dumps(message))
    response = await websocket.recv()
    return json.loads(response)


# 主函数
async def main():
    uri = 'wss://www.deribit.com/ws/api/v2'
    async with websockets.connect(uri) as websocket:
        # 步骤1：进行身份验证
        auth_message = create_auth_message()
        auth_response = await send_message(websocket, auth_message)

        if 'result' in auth_response and 'access_token' in auth_response['result']:
            print("身份验证成功")
            # 步骤2：调用私有方法获取大宗交易信息
            trade_id = "BLOCK-170990"  # 替换为您感兴趣的交易 ID
            # block_trade_message = create_block_trade_message(trade_id)
            block_trade_message = create_get_last_block_trades_message("BTC", count=10)
            block_trade_response = await send_message(websocket, block_trade_message)
            print("大宗交易信息：", block_trade_response)
        else:
            print("身份验证失败：", auth_response)


if __name__ == "__main__":
    asyncio.run(main())
