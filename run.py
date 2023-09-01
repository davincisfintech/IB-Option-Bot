import json
from threading import Thread
from time import sleep

import uvicorn
from fastapi import FastAPI
from ibapi.client import ExecutionFilter
from pydantic import BaseModel

from trading_bot.clients.ib_client import IBapi
from trading_bot.settings import logger
from trading_bot.trade_managers.tv_trade_manager import TvTradeManager

TRADING_MODE = 'Paper'  # Choices Live, Paper
ORDER_TYPE = 'LMT'   # Choices LMT, MKT. LMT for limit order and MKT for market order

# Initialize app
app = FastAPI()
client = IBapi()
socket_port = 7497 if TRADING_MODE.lower() == 'paper' else 7496
client.connect('127.0.0.1', socket_port, 123)
client_thread = Thread(target=client.run, daemon=True)
client_thread.start()
client.reqPositions()
client.reqAccountSummary(9002, "All", "$LEDGER")
client.reqAllOpenOrders()
client.reqExecutions(10001, ExecutionFilter())

# while not client.total_amount:
#     pass

sleep(1)
logger.info('Trading bot server started, running...')


class Params(BaseModel):
    """
    Alert Parameters, required: instrument, all other optional
    """
    symbol: str
    action: str
    position_size: float
    price: float


@app.post("/")
async def trigger_trade(params: Params):
    params = json.loads(params.json())
    symbol = params['symbol'].upper()
    logger.debug(f'Request received, parameters: {params}')
    if params['action'].upper() not in ['BUY', 'SELL']:
        logger.debug(f'action must be BUY or SELL, not {params["action"].upper() }')
        return {'error': 'Invalid action', 'msg': 'action must be BUY or SELL'}
    if params['position_size'] <= 0:
        logger.debug(f'position_size must be greater than 0, not {params["position_size"]}')
        return {'error': 'Invalid position_size', 'msg': 'position_size must be greater than 0'}
    if params['price'] <= 0 or params['price'] > params['position_size']:
        logger.debug(f'price must be greater than 0 and less than position_size, not {params["price"]}')
        return {'error': 'Invalid price', 'msg': 'price must be greater than 0 and less than position_size'}

    logger.debug('Parameters validated, making trade...')
    unique_id = client.nextorderId
    contract = client.make_contract(symbol, 'STK', 'SMART', 'ISLAND')

    # Initialize Trading bot
    trading_bot = TvTradeManager(client, unique_id=unique_id, trading_mode=TRADING_MODE,
                                 contract=contract, pos_limit=params['position_size'],
                                 instruction=params['action'].upper(), order_type=ORDER_TYPE, price=params['price'])

    # Make Trade
    response = trading_bot.trade()
    if response is True:
        msg = "Successfully completed trade"
        logger.debug(msg)
    else:
        msg = "Error completing trade"
        logger.debug(msg)

    return {"success": bool(response), "message": msg}


if __name__ == "__main__":
    host = "0.0.0.0"
    uvicorn.run(app, host=host, port=80, log_level="info")
