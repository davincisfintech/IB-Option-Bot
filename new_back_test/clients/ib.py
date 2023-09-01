from collections import defaultdict

import pandas as pd
from dateutil.parser import parse
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper

from new_back_test.settings import TZ, logger


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = defaultdict(list)
        self.time_frame = '1 min'
        self.data_frames = defaultdict(pd.DataFrame)

    def historicalData(self, reqId, bar):
        data = {'datetime': bar.date, 'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close,
                'volume': bar.volume}
        self.data[reqId].append(data)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        df = pd.DataFrame(self.data[reqId])
        del self.data[reqId]
        if self.time_frame in ['1 day']:
            df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(TZ)
        else:
            df['datetime'] = df['datetime'].apply(lambda x: parse(x).astimezone(TZ))
        df = df.set_index('datetime')
        self.data_frames[reqId] = df
        logger.debug(f'{reqId}: Historical Data fetched for id: {reqId}')

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        logger.info(f'The next valid order id is: {self.nextorderId}')

    def error(self, reqId, errorCode, errorString):
        logger.debug(f'Error: {errorCode}, {errorString}')

    @staticmethod
    def make_contract(symbol, security_type, exchange, prim_exchange=None, currency='USD'):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = security_type
        contract.exchange = exchange
        if prim_exchange is not None:
            contract.primaryExch = prim_exchange
        contract.currency = currency
        return contract

