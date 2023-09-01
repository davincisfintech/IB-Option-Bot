from collections import defaultdict
from datetime import datetime

import pandas as pd
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper

from back_test.settings import TZ, logger


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = defaultdict(list)
        self.extended_hours_data = True
        self.time_frame = '1 min'
        self.data_frames = defaultdict(pd.DataFrame)

    def historicalData(self, reqId, bar):
        # print(reqId, datetime.fromtimestamp(int(bar.date)), bar.open, bar.high, bar.low, bar.close)
        data = {'datetime': bar.date, 'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close,
                'volume': bar.volume}
        self.data[reqId].append(data)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        # super().historicalDataEnd(reqId, start, end)
        # print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)
        df = pd.DataFrame(self.data[reqId])
        del self.data[reqId]
        if self.time_frame in ['1 day']:
            df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(TZ)
        else:
            df['datetime'] = df['datetime'].apply(lambda x: datetime.fromtimestamp(int(x)).astimezone(TZ))
        df = df.set_index('datetime')
        if not self.extended_hours_data:
            df = df.between_time('09:30', '15:59')
        self.data_frames[reqId] = df
        logger.debug(f'{reqId}: Historical Data fetched for id: {reqId}')

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        print('The next valid order id is: ', self.nextorderId)

    def error(self, reqId, errorCode, errorString):
        ...  # print('Error:', errorCode, errorString)

    @staticmethod
    def make_contract(symbol, sec_type, exch, prim_exch=None, curr='USD'):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exch
        contract.primaryExch = prim_exch
        contract.currency = curr
        return contract

