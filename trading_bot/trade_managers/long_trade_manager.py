import uuid
from datetime import datetime

from trading_bot.clients.order_samples import OrderSamples
from trading_bot.settings import logger, TZ


class TradeManager:
    def __init__(self, client, unique_id, trading_mode, contract, pos_limit, stop_loss, target, entry_order_type,
                 ltp=None, side=None, entered=False, entry_order_filled=False, exit_order_filled=False,
                 bought=False, sold=False, instruction=None, qty=None, sl=None, tr=None, trade_id=None,
                 entry_order_id=None, entry_order_price=None,
                 exit_pending=False, entry_order_status=None, sl_exit_order_id=None, sl_exit_order_price=None,
                 tr_exit_order_id=None, tr_exit_order_price=None):
        self.client = client
        self.id = unique_id
        self.trading_mode = trading_mode
        self.contract = contract
        self.symbol = contract.symbol
        self.pos_limit = pos_limit
        self.target = target
        self.stop_loss = stop_loss
        self.short_allowed = True
        self.ltp = ltp
        self.ltp_time = None
        self.side = side
        self.entered = entered
        self.bought = bought
        self.sold = sold
        self.instruction = instruction
        self.qty = qty
        self.sl = sl
        self.tr = tr
        self.entry_order_type = entry_order_type
        self.entry_order_price = entry_order_price
        self.entry_order_time = None
        self.entry_order_id = entry_order_id
        self.entry_order_filled = entry_order_filled
        self.entry_order_status = entry_order_status
        self.entry_price = None
        self.entry_time = None
        self.sl_exit_order_time = None
        self.sl_exit_order_price = sl_exit_order_price
        self.sl_exit_order_id = sl_exit_order_id
        self.sl_exit_order_status = None
        self.tr_exit_order_time = None
        self.tr_exit_order_price = tr_exit_order_price
        self.tr_exit_order_id = tr_exit_order_id
        self.tr_exit_order_status = None
        self.exit_order_filled = exit_order_filled
        self.exit_pending = exit_pending
        self.exit_time = None
        self.exit_price = None
        self.exit_type = None
        self.position_status = None
        self.trade_ended = False
        self.position_check = True
        self.market_depth_check = False
        self.messages = []
        self.trade_id = str(uuid.uuid4()) if trade_id is None else trade_id
        logger.debug(f"""{trading_mode} Trading bot {self.symbol} instance started, parameters: unique ID: {self.id}, 
                         position limit: {self.pos_limit} USD, target : {self.target}, stop loss: {self.stop_loss},
                         trade_id: {self.trade_id}""")

    def __repr__(self):
        return f"trading_mode: {self.trading_mode}, id: {self.id}, instrument: {self.symbol}, trade_id: {self.trade_id}"

    def trade(self):
        if self.trade_ended:
            return self

        self.messages = []

        if not self.entered:
            if self.ltp is None:
                ltp_data = self.client.ltp_data[self.id].get() if not self.client.ltp_data[self.id].empty() else {}
                self.ltp = ltp_data.get('ltp')

                if self.ltp is None:
                    return
                self.client.cancelTickByTickData(self.id)

        if self.is_valid_entry():
            self.make_entry()

        if self.entered and not self.entry_order_filled:
            self.confirm_entry()

        if self.is_valid_exit():
            self.make_exit()

        if self.entered and self.exit_pending:
            self.confirm_exit()

        return {'msg': self.messages}

    def is_valid_entry(self):
        if self.entered:
            return False

        if not self.market_depth_check and not len(self.client.l2_data[self.id]) > 100:
            return
        # print(self.symbol, len(self.client.l2_data[self.id]), self.client.l2_data[self.id][:5])

        end_trade = False

        if not self.market_depth_check:
            bids = [i for i in self.client.l2_data[self.id] if i['side'] == 1]
            asks = [i for i in self.client.l2_data[self.id] if i['side'] == 0]
            bid_length = len(bids)
            ask_length = len(asks)
            bid_size = sum([i['size'] for i in bids])
            ask_size = sum([i['size'] for i in asks])
            bid_price_level = sum([i['price'] for i in bids]) / bid_length
            ask_price_level = sum([i['price'] for i in asks]) / ask_length

            if self.instruction == 'BUY':
                if bid_length < ask_length:
                    end_trade = True
                    logger.debug(f'{self.symbol}: Market depth length condition failed for {self.instruction}, '
                                 f'bids length: {bid_length}, asks length: {ask_length}')
                if bid_size <= ask_size:
                    logger.debug(f'{self.symbol}: Market depth size condition failed for {self.instruction}, '
                                 f'bids size: {bid_size}, asks size: {ask_size}')
                    end_trade = True
                if bid_price_level > self.ltp:
                    logger.debug(f'{self.symbol}: Market depth price level condition failed for {self.instruction}, '
                                 f'bids price level: {bid_price_level}, order price: {self.ltp}')
                    end_trade = True

            if not self.market_depth_check and self.instruction == 'SELL':
                if ask_length < bid_length:
                    logger.debug(f'{self.symbol}: Market depth length condition failed for {self.instruction}, '
                                 f'bids length: {bid_length}, asks length: {ask_length}')
                    end_trade = True
                if ask_size <= bid_size:
                    logger.debug(f'{self.symbol}: Market depth size condition failed for {self.instruction}, '
                                 f'bids size: {bid_size}, asks size: {ask_size}')
                    end_trade = True
                if ask_price_level < self.ltp:
                    logger.debug(f'{self.symbol}: Market depth price level condition failed for {self.instruction}, '
                                 f'bids price level: {bid_price_level}, order price: {self.ltp}')
                    end_trade = True

        if end_trade:
            self.client.cancelMktDepth(self.id, True)
            logger.debug(f'{self.symbol}: Market depth condition failed for {self.instruction}, closing instance')
            self.trade_ended = True
            return
        else:
            if not self.market_depth_check:
                logger.debug(f'{self.symbol}: All Market depth conditions satisfied for {self.instruction}')
                self.market_depth_check = True
                self.client.cancelMktDepth(self.id, True)

        if self.instruction == 'BUY' and self.client.open_stocks_limit > 0:
            logger.info(f'Long signal generated for {self.symbol} at {datetime.now(tz=TZ)}, price: {self.ltp}')
            self.bought = True
            self.instruction = 'BUY'
            return True
        if self.short_allowed and self.instruction == 'SELL' and self.client.open_stocks_limit > 0:
            logger.info(f'Short signal generated for {self.symbol} at {datetime.now(tz=TZ)}, price: {self.ltp}')
            self.sold = True
            self.instruction = 'SELL'
            return True

    def is_valid_exit(self):
        if not self.entered or not self.entry_order_filled or self.exit_pending:
            return False

        close_entry_in_db = False

        if self.bought:
            if self.position_check:
                for pos in self.client.positions:
                    if pos['symbol'] == self.symbol and pos['position'] >= self.qty:
                        self.instruction = 'SELL'
                        return True
                else:
                    logger.debug(f'{self.symbol} No long position exist for qty: {self.qty}')
                    close_entry_in_db = True
            else:
                self.instruction = 'SELL'
                self.position_check = True
                return True

        elif self.sold:
            if self.position_check:
                for pos in self.client.positions:
                    if pos['symbol'] == self.symbol and pos['position'] <= -self.qty:
                        self.instruction = 'BUY'
                        return True
                else:
                    logger.debug(f'{self.symbol} No short position exist for qty: {self.qty}')
                    close_entry_in_db = True
            else:
                self.instruction = 'BUY'
                self.position_check = True
                return True

        if close_entry_in_db:
            self.exit_type, self.exit_time, self.exit_price = None, None, None
            self.sl_exit_order_status, self.tr_exit_order_status, self.position_status = None, None, None
            self.entered, self.bought, self.sold, self.exit_pending = False, False, False, False
            self.client.open_stocks_limit += 1
            confirm_exit_data = self.save_trade(action='confirm_exit')
            self.messages.append(confirm_exit_data)
            self.trade_ended = True
            logger.debug(f'{self.symbol}: Trade completed, closing instance')

    def make_entry(self):
        price = float("{:0.2f}".format(self.ltp))
        self.qty = int(self.pos_limit / self.ltp)
        if self.qty < 1:
            logger.debug(f'{self.symbol} Quantity less than 0, please increase position limit')
            self.trade_ended = True
            return

        if (self.qty * self.ltp) > self.client.total_amount:
            logger.debug(f'{self.symbol} Not enough funds to take position, position size: {(self.qty * price)}, '
                         f'funds available: {self.client.total_amount}')
            self.trade_ended = True
            return

        if self.client.open_stocks_limit <= 0:
            # logger.debug(f'{self.symbol}, stocks limit is reached so ignoring entry')
            return

        self.client.nextorderId += 1
        self.entry_order_id = self.client.nextorderId
        self.client.placeOrder(self.entry_order_id, self.contract,
                               self.client.make_order(self.instruction, self.qty,
                                                      order_type=self.entry_order_type, price=price))
        self.entry_order_price = price
        self.entry_order_time = datetime.now(tz=TZ)
        self.entered = True
        self.side = self.instruction
        self.entry_order_filled = False
        self.entry_order_status = 'OPEN'

        # Update account balance after taking position
        self.client.reqAccountSummary(9002, "All", "$LEDGER")

        self.client.open_stocks_limit -= 1

        logger.debug(f"""Entry order Placed to {self.instruction} {self.qty} {self.symbol}, 
                         price: {self.entry_order_price}, time:{self.entry_order_time}, 
                         order id: {self.entry_order_id}""")
        self.trade_id = str(uuid.uuid4())
        logger.debug(f'{self.symbol} Instance, new trade_id: {self.trade_id}')
        entry_data = self.save_trade(action='make_entry')
        self.messages.append(entry_data)

    def make_exit(self):
        self.client.nextorderId += 1
        oco_id = str(self.client.nextorderId)

        self.client.nextorderId += 1
        self.tr_exit_order_id = self.client.nextorderId
        self.client.nextorderId += 1
        self.sl_exit_order_id = self.client.nextorderId

        self.tr_exit_order_price = float("{:0.2f}".format(self.tr))
        self.sl_exit_order_price = float("{:0.2f}".format(self.sl))
        oca_orders = [OrderSamples.LimitOrder(action=self.instruction, quantity=self.qty,
                                              limitPrice=self.tr_exit_order_price),
                      OrderSamples.Stop(action=self.instruction, quantity=self.qty, stopPrice=self.sl_exit_order_price)
                      # OrderSamples.StopLimit(action=self.instruction, quantity=self.qty,
                      #                        limitPrice=self.sl_exit_order_price, stopPrice=self.sl_exit_order_price)
                      ]

        OrderSamples.OneCancelsAll("OCA_" + oco_id, oca_orders, 1)

        for order, order_id in zip(oca_orders, [self.tr_exit_order_id, self.sl_exit_order_id]):
            if order_id == self.sl_exit_order_id:
                self.sl_exit_order_time = datetime.now(tz=TZ)
            else:
                self.tr_exit_order_time = datetime.now(tz=TZ)
            self.client.placeOrder(order_id, self.contract, order)

        self.sl_exit_order_status = 'OPEN'
        self.tr_exit_order_status = 'OPEN'
        self.exit_order_filled = False
        self.exit_pending = True
        logger.debug(f"""Exit SL and Target order Placed to {self.instruction} {self.qty} {self.symbol}, 
                         SL order price: {self.sl_exit_order_price}, Target order price: {self.tr_exit_order_price}
                         SL order time time:{self.sl_exit_order_time}, SL order id: {self.sl_exit_order_id}, 
                         Target order time time:{self.tr_exit_order_time}, Target order id: {self.tr_exit_order_id}""")
        exit_data = self.save_trade(action='make_exit')
        self.messages.append(exit_data)

    def confirm_entry(self):
        for exec_order in self.client.exec_orders:
            if str(exec_order['exec_order_id']) == str(self.entry_order_id) and exec_order['symbol'] == self.symbol:
                self.entry_price = exec_order['exec_avg_price']
                self.entry_time = exec_order['exec_time']
                self.entry_order_filled = True
                self.entry_order_status = 'FILLED'
                self.position_status = 'OPEN'
                if self.bought:
                    self.tr = self.entry_price * (1 + (self.target / 100))
                    self.sl = self.entry_price * (1 - (self.stop_loss / 100))
                else:
                    self.tr = self.entry_price * (1 - (self.target / 100))
                    self.sl = self.entry_price * (1 + (self.stop_loss / 100))
                logger.debug(
                    f"Entry order Filled to {self.instruction} {self.symbol}, price: {self.entry_price},"
                    f" qty:{self.qty}, time:{self.entry_time}, SL: {self.sl}, Target: {self.tr}")
                entry_data = self.save_trade(action='confirm_entry')
                self.position_check = False
                self.messages.append(entry_data)
                return

        for order in self.client.orders:
            if str(order['order_id']) == str(self.entry_order_id) and order['status'] in ['Cancelled', 'Inactive']:
                logger.debug(f'{self.symbol} Entry order to {self.instruction} {order["status"]}')
                self.entered = False
                self.bought, self.sold = False, False
                self.entry_time = None
                self.entry_price = None
                self.tr = None
                self.sl = None
                self.entry_order_status = order['status']
                self.position_status = None

                self.client.open_stocks_limit += 1
                entry_data = self.save_trade(action='confirm_entry')
                self.messages.append(entry_data)
                self.trade_ended = True
                logger.info(f'{self.symbol}, Entry order cancelled, Closing instance')
                return

    def confirm_exit(self):
        for exec_order in self.client.exec_orders:
            if exec_order['symbol'] != self.symbol:
                continue
            exec_order_id = str(exec_order['exec_order_id'])
            if exec_order_id == str(self.sl_exit_order_id) or exec_order_id == str(self.tr_exit_order_id):
                self.exit_price = exec_order['exec_avg_price']
                self.exit_time = exec_order['exec_time']
                if exec_order_id == str(self.sl_exit_order_id):
                    self.exit_type = 'SL'
                    self.sl_exit_order_status = 'FILLED'
                    self.tr_exit_order_status = 'CANCELED'
                else:
                    self.exit_type = 'Target'
                    self.sl_exit_order_status = 'CANCELED'
                    self.tr_exit_order_status = 'FILLED'
                self.position_status = 'CLOSED'
                self.bought, self.sold = False, False
                self.exit_order_filled = True
                self.entered = False
                self.exit_pending = False
                self.client.open_stocks_limit += 1
                logger.debug(f"""Exit {self.exit_type} order Filled to {self.instruction} {self.qty} {self.symbol}, 
                                 price: {self.exit_price}, time:{self.exit_time}, order id: {self.sl_exit_order_id}""")
                exit_data = self.save_trade(action='confirm_exit')
                self.messages.append(exit_data)
                self.trade_ended = True
                logger.debug(f'{self.symbol}: Trade completed, closing instance')
                return

        order_cancelled = 0
        order_status = None
        for order in self.client.orders:
            order_id = str(order['order_id'])
            if order_id == str(self.sl_exit_order_id) or order_id == str(self.tr_exit_order_id):
                if order['status'] in ['Cancelled', 'Inactive']:
                    order_cancelled += 1
                    order_status = order['status']

        if order_cancelled == 2:
            logger.debug(f'{self.symbol} Exit order to {self.instruction}, status: {order_status}')
            # self.exit_type, self.exit_price, self.exit_time = None, None, None
            # self.sl_exit_order_status = self.tr_exit_order_status = order['status']
            # self.entered, self.bought, self.sold = False, False, False
            self.exit_pending = False
            # self.position_status = None
            # exit_data = self.save_trade(action='confirm_exit')
            # self.messages.append(exit_data)
            return

    def save_trade(self, action):
        message = dict()
        if action == 'make_entry':
            message[action] = {'symbol': self.symbol, 'side': self.side, 'entry_order_time': self.entry_order_time,
                               'entry_order_price': self.entry_order_price, 'instruction': self.instruction,
                               'entry_order_id': self.entry_order_id, 'entry_order_status': self.entry_order_status,
                               'quantity': self.qty, 'trade_id': self.trade_id, 'trading_mode': self.trading_mode}
            return message

        elif action == 'confirm_entry':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'entry_time': self.entry_time,
                               'entry_price': self.entry_price, 'stop_loss': self.sl, 'target': self.tr,
                               'entry_order_status': self.entry_order_status, 'position_status': self.position_status}
            return message

        elif action == 'make_exit':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'instruction': self.instruction,
                               'sl_exit_order_id': self.sl_exit_order_id, 'tr_exit_order_id': self.tr_exit_order_id,
                               'sl_exit_order_time': self.sl_exit_order_time,
                               'tr_exit_order_time': self.tr_exit_order_time,
                               'sl_exit_order_price': self.sl_exit_order_price,
                               'tr_exit_order_price': self.tr_exit_order_price,
                               'sl_exit_order_status': self.sl_exit_order_status,
                               'tr_exit_order_status': self.tr_exit_order_status}
            return message

        elif action == 'confirm_exit':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'exit_time': self.exit_time,
                               'exit_price': self.exit_price, 'exit_type': self.exit_type,
                               'sl_exit_order_status': self.sl_exit_order_status,
                               'tr_exit_order_status': self.tr_exit_order_status,
                               'position_status': self.position_status}
            return message
