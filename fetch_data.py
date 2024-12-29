import asyncio
import websockets
import json


MSG_AUTH = \
    {
        "jsonrpc": "2.0",
        "id": 9929,
        "method": "public/auth",
        "params": {
            "grant_type": "client_credentials",
            "client_id": "XXXXX",
            "client_secret": "YYYYYYYYY"
        }
    }


async def call_api(msg):
    uri = 'wss://www.deribit.com/ws/api/v2'
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(msg))
        try:
            response = await websocket.recv()
            return json.loads(response) # return the json decode
        except websockets.exceptions.ConnectionClosedOK:
            return {"error": "Connection closed cleanly."}
        except websockets.exceptions.ConnectionClosedError as e:
            return {"error": f"Connection closed with error: {e}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}
        except json.JSONDecodeError as e:
            return {"error": f"JSON decoding error: {e}"}


if __name__ == "__main__":
    asyncio.run(call_api(MSG_AUTH))


