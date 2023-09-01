import uuid
from datetime import datetime

from trading_bot.database.db import TradesData
from trading_bot.settings import logger, TZ


class TvTradeManager:
    def __init__(self, client, trading_mode, contract, pos_limit, instruction, order_type, price=None):
        self.client = client
        self.trading_mode = trading_mode
        self.contract = contract
        self.symbol = contract.symbol
        self.pos_limit = pos_limit
        self.order_type = order_type
        self.short_allowed = False
        self.instruction = instruction
        self.order_price = price
        self.quantity = int(self.pos_limit / price)
        self.entered = False
        self.order_time = None
        self.order_id = None
        self.order_status = None
        self.entry_price = None
        self.entry_time = None
        self.trade_id = str(uuid.uuid4())
        logger.debug(f"""{trading_mode} Trading bot {self.symbol} instance started, parameters: 
                         position limit: {self.pos_limit} USD, instruction: {self.instruction},
                         trade_id: {self.trade_id}""")

    def __repr__(self):
        return f"trading_mode: {self.trading_mode}, instrument: {self.symbol}, trade_id: {self.trade_id}"

    def trade(self):
        if self.is_valid_entry():
            self.make_entry()
        if self.entered:
            self.confirm_entry()
            self.save_trade()
            return True

    def is_valid_entry(self):
        self.quantity = int(self.pos_limit / self.order_price)
        if self.quantity < 1:
            logger.debug(f'{self.symbol} Quantity less than 0, closing instance, please increase position limit')
            return

        if (self.quantity * self.order_price) > self.client.total_amount:
            logger.debug(f'{self.symbol} Not enough funds to take position, '
                         f'position size: {(self.quantity * self.order_price)}, '
                         f'funds available: {self.client.total_amount}')
            return
        if self.instruction == 'BUY':
            return True
        elif self.instruction == 'SELL':
            if self.short_allowed:
                return True
            else:
                for pos in self.client.positions:
                    if pos['symbol'] == self.symbol and pos['position'] >= self.quantity:
                        self.instruction = 'SELL'
                        return True
                else:
                    logger.debug(f'{self.symbol} No long position exist for qty: {self.quantity}')

    def make_entry(self):
        self.order_price = float("{:0.2f}".format(self.order_price))
        self.client.nextorderId += 1
        self.order_id = self.client.nextorderId
        self.client.placeOrder(self.order_id, self.contract,
                               self.client.make_order(self.instruction, self.quantity, order_type=self.order_type,
                                                      price=self.order_price))
        self.order_time = datetime.now(tz=TZ)
        self.order_status = 'Open'
        self.entered = True

        # Update account balance after taking position
        self.client.reqAccountSummary(9002, "All", "$LEDGER")

        logger.debug(
            f"Order Placed to {self.instruction} {self.symbol}, price: {self.order_price}, quantity:{self.quantity}, "
            f"time:{self.order_time}, order id: {self.order_id}")

    def confirm_entry(self):
        for exec_order in self.client.exec_orders:
            if str(exec_order['exec_order_id']) == str(self.order_id) and exec_order['symbol'] == self.symbol:
                self.entry_price = exec_order['exec_avg_price']
                self.entry_time = exec_order['exec_time']
                self.order_status = 'Filled'
                logger.debug(
                    f"Order Filled to {self.instruction} {self.symbol}, price: {self.entry_price},"
                    f" qty:{self.quantity}, time:{self.entry_time}")
                return

        for order in self.client.orders:
            if str(order['order_id']) == str(self.order_id):
                self.order_status = order['status']
                logger.debug(f'{self.symbol} Order to {self.instruction} {order["status"]}')
                return

    def save_trade(self):
        obj = TradesData(symbol=self.symbol, instruction=self.instruction,
                         order_time=self.order_time,
                         order_price=self.order_price, order_id=self.order_id,
                         order_status=self.order_status, quantity=self.quantity, trade_id=self.trade_id,
                         trading_mode=self.trading_mode, entry_price=self.entry_price,
                         entry_time=self.entry_time)
        obj.save_to_db()
        logger.debug(f'Trade Saved for {self.symbol}')
