from collections import defaultdict
from queue import Queue
from datetime import datetime

import pandas as pd
from dateutil.parser import parse
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper
from ibapi.scanner import ScannerSubscription
from ibapi.scanner import ScanData

from trading_bot.settings import TZ, logger


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.orders = []
        self.exec_orders = []
        self.positions = []
        self.total_amount = 0
        self.open_stocks_limit = 0
        self.l2_data = defaultdict(list)
        self.ltp_data = defaultdict(Queue)
        self.scanned_contracts = dict()

        self.data = defaultdict(list)
        self.extended_hours_data = True
        self.time_frame = '1 min'
        self.data_frames = defaultdict(pd.DataFrame)

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        print('The next valid order id is: ', self.nextorderId)

    def orderStatus(self, orderId, status, filled, remaining, avgFullPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice):
        self.orders.append({'order_id': orderId, 'status': status, 'avg_price': avgFullPrice, 'filled': filled})
        # print('orderStatus - orderid:', orderId, 'status:', status, 'filled', filled, 'remaining', remaining,
        #       'lastFillPrice', lastFillPrice)

    def execDetails(self, reqId, contract, execution):
        self.exec_orders.append({'order_id': reqId, 'symbol': contract.symbol, 'exec_order_id': execution.orderId,
                                 'exec_avg_price': execution.avgPrice,
                                 'exec_time': parse(execution.time).astimezone(TZ)})

        # print('Order Executed: ', reqId, contract.symbol, contract.secType, contract.currency, execution.execId,
        #       execution.orderId, execution.shares, execution.lastLiquidity, execution.avgPrice)

    def position(self, account: str, contract: Contract, position, avgCost: float):
        super().position(account, contract, position, avgCost)
        for pos in self.positions:
            if pos['symbol'] == contract.symbol:
                pos['position'] = position
                pos['avg_cost'] = avgCost
                break
        else:
            self.positions.append({'symbol': contract.symbol, 'position': position, 'avg_cost': avgCost})
        # print("Position.", "Account:", account, "Symbol:", contract.symbol, "SecType:", contract.secType,
        #       "Currency:", contract.currency, "Position:", position, "Avg cost:", avgCost)

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        if tag == 'TotalCashBalance':
            self.total_amount = float(value)
            # print('total amount', self.total_amount)
        # print("AccountSummary. ReqId:", reqId, "Account:", account, "Tag: ", tag, "Value:", value, "Currency:",
        #       currency)

    def tickByTickAllLast(self, reqId, tickType, time, price, size, tickAtrribLast, exchange, specialConditions):
        # print(reqId, tickType, time, price, size, datetime.fromtimestamp(int(time)).astimezone(TZ))
        # self.queue.put({'id': reqId, 'ltp_time': datetime.fromtimestamp(int(time)).astimezone(TZ), 'ltp': price})
        # print({'id': reqId, 'ltp_time': time, 'ltp': price})
        self.ltp_data[reqId].put({'id': reqId, 'ltp_time': datetime.fromtimestamp(int(time)).astimezone(TZ),
                                  'ltp': price})

    def historicalData(self, reqId, bar):
        # print(reqId, datetime.fromtimestamp(int(bar.date)), bar.open, bar.high, bar.low, bar.close)
        data = {'datetime': bar.date, 'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close,
                'volume': bar.volume}
        self.data[reqId].append(data)

    def historicalDataUpdate(self, reqId, bar):
        if self.time_frame in ['1 day']:
            bar_date_time = parse(bar.date).astimezone(tz=TZ)
        else:
            bar_date_time = datetime.fromtimestamp(int(bar.date)).astimezone(TZ)

        data = {'open': bar.open, 'high': bar.high, 'low': bar.low, 'close': bar.close, 'volume': bar.volume}

        if not len(self.data_frames[reqId]):
            df = pd.DataFrame(self.data[reqId])
            del self.data[reqId]
            if self.time_frame in ['1 day']:
                df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(TZ)
                df['datetime'] = df['datetime'].dt.date
            else:
                df['datetime'] = df['datetime'].apply(lambda x: datetime.fromtimestamp(int(x)).astimezone(TZ))
            df = df.set_index('datetime')
            if not self.extended_hours_data:
                df = df.between_time('09:30', '15:59')
            daily = pd.DataFrame(
                df.between_time('04:00', '15:59').groupby(pd.Grouper(freq='1D'))['close'].last().dropna(axis=0))
            daily['close'] = daily['close'].shift(1)
            try:
                df = pd.merge_asof(df, daily, right_index=True, left_index=True)
                df.columns = ['open', 'high', 'low', 'close', 'volume', 'prev_close']
                df = df[df.index.date == df.index[-1].date()]
                self.data_frames[reqId] = df
                logger.debug(f'{reqId}: Historical Data fetched for id: {reqId}')
            except Exception as e:
                logger.exception(e)
                return

        self.data_frames[reqId].loc[bar_date_time] = data
        # print(reqId, bar_date_time, data)
        # print(self.data_frames[reqId])

    def mktDepthExchanges(self, depthMktDataDescriptions):
        super().mktDepthExchanges(depthMktDataDescriptions)
        print("MktDepthExchanges:")
        for desc in depthMktDataDescriptions:
            print("DepthMktDataDescription.", desc)

    def updateMktDepth(self, reqId, position, operation, side, price, size):
        super().updateMktDepth(reqId, position, operation, side, price, size)
        print("UpdateMarketDepth. ReqId:", reqId, "Position:", position, "Operation:",
              operation, "Side:", side, "Price:", price, "Size:", size)

    def updateMktDepthL2(self, reqId, position, marketMaker, operation, side, price, size, isSmartDepth):
        super().updateMktDepthL2(reqId, position, marketMaker, operation, side, price, size, isSmartDepth)
        self.l2_data[reqId].append({'position': position, 'market_maker': marketMaker, 'operation': operation,
                                    'side': side, 'price': price, 'size': size})
        # print("UpdateMarketDepthL2. ReqId:", reqId, "Position:", position, "MarketMaker:", marketMaker, "Operation:",
        #       operation, "Side:", side, "Price:", price, "Size:", size, "isSmartDepth:", isSmartDepth)

    def error(self, reqId, errorCode, errorString):
        pass
        # print('Error:', errorCode, errorString)

    def scannerData(self, reqId: int, rank: int, contractDetails, distance: str, benchmark: str, projection: str,
                    legsStr: str):
        super().scannerData(reqId, rank, contractDetails, distance, benchmark, projection, legsStr)
        if reqId not in self.scanned_contracts:
            self.scanned_contracts[reqId] = dict()
        self.scanned_contracts[reqId][rank] = contractDetails.contract
        # print("ScannerData. ReqId:", reqId,
        #       ScanData(contractDetails.contract, rank, distance, benchmark, projection, legsStr))

    def scannerDataEnd(self, reqId: int):
        super().scannerDataEnd(reqId)
        # print("ScannerDataEnd. ReqId:", reqId)

    @staticmethod
    def get_sub(scan_name, above_price, below_price, above_volume, average_volume, market_cap_usd,
                limit=10):
        scan_sub = ScannerSubscription()
        scan_sub.instrument = "STK"
        scan_sub.locationCode = "STK.US.MAJOR"
        scan_sub.scanCode = scan_name
        scan_sub.abovePrice = above_price
        scan_sub.belowPrice = below_price
        scan_sub.aboveVolume = above_volume
        scan_sub.avgVolumeAbove = average_volume
        scan_sub.usdMarketCapAbove = market_cap_usd
        scan_sub.numberOfRows = limit
        return scan_sub

    @staticmethod
    def make_contract(symbol, sec_type, exch, prim_exch=None, curr='USD'):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exch
        contract.primaryExch = prim_exch
        contract.currency = curr
        return contract

    @staticmethod
    def make_order(action, quantity, order_type, price=None, stop_price=None):
        order = Order()
        order.orderType = order_type
        order.totalQuantity = quantity
        order.action = action
        order.tif = 'GTD'
        order.goodTillDate = datetime.now().strftime('%Y%m%d 19:59:10 US/Eastern')
        order.Transmit = True
        if order_type == 'LMT':
            order.lmtPrice = price
        elif order_type == 'STP LMT':
            order.auxPrice = stop_price
            order.lmtPrice = price
        elif order_type == 'STP':
            order.auxPrice = stop_price

        return order
