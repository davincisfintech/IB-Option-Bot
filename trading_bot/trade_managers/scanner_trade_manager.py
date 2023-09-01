import uuid
from datetime import datetime

from trading_bot.settings import logger, TZ


class TradeManager:
    def __init__(self, client, unique_id, trading_mode, contract, pos_limit, entry_order_type, rank, exit_percent,
                 top_gainers_to_trade, rsi_period, rsi_upper_threshold, rsi_lower_threshold, average_volume_period,
                 short_sma_period, long_sma_period, average_volume, above_volume, scan_name,
                 exit_order_type='MKT', ltp=None, side=None, entered=False, entry_order_filled=False,
                 exit_order_filled=False, bought=False, sold=False, instruction=None, qty=None, trade_id=None,
                 entry_order_id=None, entry_order_price=None, exit_pending=False, entry_order_status=None,
                 exit_order_id=None, exit_order_price=None, initial_change=None):
        self.client = client
        self.id = unique_id
        self.trading_mode = trading_mode
        self.contract = contract
        self.symbol = contract.symbol
        self.pos_limit = pos_limit
        self.rank = rank
        self.exit_order_type = entry_order_type
        self.exit_percent = exit_percent
        self.top_gainers_to_trade = top_gainers_to_trade
        self.rsi_period = rsi_period
        self.rsi_upper_threshold = rsi_upper_threshold
        self.rsi_lower_threshold = rsi_lower_threshold
        self.average_volume_period = average_volume_period
        self.short_sma_period = short_sma_period
        self.long_sma_period = long_sma_period
        self.average_volume = average_volume
        self.above_volume = above_volume
        self.scan_name = scan_name
        self.short_allowed = True
        self.ltp = ltp
        self.ltp_time = None
        self.side = side
        self.entered = entered
        self.bought = bought
        self.sold = sold
        self.instruction = instruction
        self.qty = qty
        self.entry_order_type = entry_order_type
        self.entry_order_price = entry_order_price
        self.entry_order_time = None
        self.entry_order_id = entry_order_id
        self.entry_order_filled = entry_order_filled
        self.entry_order_status = entry_order_status
        self.entry_price = None
        self.entry_time = None
        self.exit_order_time = None
        self.exit_order_price = exit_order_price
        self.exit_order_id = exit_order_id
        self.exit_order_status = None
        self.exit_order_filled = exit_order_filled
        self.exit_pending = exit_pending
        self.exit_time = None
        self.exit_price = None
        self.exit_type = None
        self.position_status = None
        self.trade_ended = False
        self.position_check = True
        self.prev_close = None
        self.initial_change = initial_change
        self.current_change = None
        self.data = None
        self.rsi = None
        self.avg_vol = None
        self.short_sma = None
        self.long_sma = None
        self.total_vol = None
        self.messages = []
        self.trade_id = str(uuid.uuid4()) if trade_id is None else trade_id
        logger.debug(f"""{trading_mode} Trading bot {self.symbol} instance started, parameters: unique ID: {self.id}, 
                         position limit: {self.pos_limit} USD, top gainers rank : {self.rank}, 
                         exit percent: {self.exit_percent}, trade_id: {self.trade_id}, 
                         instruction: {self.instruction}, side: {self.side}, scan name: {self.scan_name}""")

    def __repr__(self):
        return f"trading_mode: {self.trading_mode}, id: {self.id}, instrument: {self.symbol}, trade_id: {self.trade_id}"

    def relative_strength_index(self, base="close"):
        delta = self.data[base].diff()
        up, down = delta.copy(), delta.copy()

        up[up < 0] = 0
        down[down > 0] = 0

        r_up = up.ewm(com=self.rsi_period - 1, adjust=False).mean()
        r_down = down.ewm(com=self.rsi_period - 1, adjust=False).mean().abs()

        self.data['rsi'] = 100 - 100 / (1 + r_up / r_down)
        self.data['rsi'].fillna(0, inplace=True)

    def trade(self):
        if self.trade_ended:
            return self

        self.data = self.client.data_frames[self.id]
        if len(self.data) < 2:
            return

        self.ltp = self.data['close'].iloc[-1]
        if not self.ltp:
            self.trade_ended = True
            logger.debug(f'{self.symbol}: Error retrieving ltp or invalid ltp: {self.ltp} received so closing instance')
            return
        if self.prev_close is None:
            self.prev_close = self.data['prev_close'].iloc[0]
        if self.initial_change is None:
            self.initial_change = ((self.ltp - self.prev_close) / self.prev_close) * 100
            if self.side is None:
                self.side = 'BUY' if self.initial_change >= 0 else 'SELL'
            logger.debug(f'{self.symbol}, scan_name: {self.scan_name}, side: {self.side}, rank: {self.rank}, '
                         f'gain: {self.initial_change}, ltp: {self.ltp}')
        else:
            self.current_change = ((self.ltp - self.prev_close) / self.prev_close) * 100

        try:
            self.relative_strength_index()
            self.data['avg_vol'] = self.data['volume'].rolling(self.average_volume_period).mean()
            self.data['short_sma'] = self.data['close'].rolling(self.short_sma_period).mean()
            self.data['long_sma'] = self.data['close'].rolling(self.long_sma_period).mean()
        except Exception as e:
            logger.exception(e)
            return

        self.messages = []

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

        if self.rank >= self.top_gainers_to_trade:
            return False
        try:
            self.rsi = self.data['rsi'].iloc[-1]
            self.avg_vol = self.data['avg_vol'].iloc[-1]
            self.short_sma = self.data['short_sma'].iloc[-1]
            self.long_sma = self.data['long_sma'].iloc[-1]
            self.total_vol = self.data['volume'].sum()
        except Exception as e:
            logger.exception((self.symbol, e))
            self.trade_ended = True
            logger.debug(f'{self.symbol}: Error getting data, closing instance')
            return

        if self.side == 'BUY' and self.client.open_stocks_limit > 0 and self.rsi >= self.rsi_upper_threshold and \
                self.avg_vol >= self.average_volume and self.short_sma > self.long_sma and self.total_vol >= self.above_volume:
            logger.info(f'Long signal generated for {self.symbol} at {datetime.now(tz=TZ)}, price: {self.ltp}, '
                        f'RSI: {self.rsi}, avg vol: {self.avg_vol}, short sma: {self.short_sma}, '
                        f'long sma: {self.long_sma}')
            self.bought = True
            self.instruction = 'BUY'
            return True

        if self.short_allowed and self.side == 'SELL' and self.client.open_stocks_limit > 0 and \
                self.rsi <= self.rsi_lower_threshold and \
                self.avg_vol >= self.average_volume and self.short_sma < self.long_sma and self.total_vol >= self.above_volume:
            logger.info(f'Short signal generated for {self.symbol} at {datetime.now(tz=TZ)}, price: {self.ltp}, '
                        f'RSI: {self.rsi}, avg vol: {self.avg_vol}, short sma: {self.short_sma}, '
                        f'long sma: {self.long_sma}')
            self.sold = True
            self.instruction = 'SELL'
            return True

    def is_valid_exit(self):
        if not self.entered or not self.entry_order_filled or self.exit_pending:
            return False

        if (self.initial_change - self.current_change) >= self.exit_percent:
            self.exit_type = 'Drop in gain'
        elif (self.initial_change - self.current_change) <= -self.exit_percent:
            self.exit_type = 'Rise in gain'
        else:
            return
        logger.debug(f'{self.symbol}: current gain: {self.current_change} {self.exit_type} '
                     f'initial gain: {self.initial_change} '
                     f'by exit change percent of {self.exit_percent} so making  exit')

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
            self.exit_order_status, self.position_status = None, None
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
        self.exit_order_id = self.client.nextorderId

        self.exit_order_price = float("{:0.2f}".format(self.ltp))

        self.client.placeOrder(self.exit_order_id, self.contract,
                               self.client.make_order(self.instruction, self.qty,
                                                      order_type=self.exit_order_type, price=self.exit_order_price))

        self.exit_order_time = datetime.now(tz=TZ)
        self.exit_order_status = 'OPEN'
        self.exit_order_filled = False
        self.exit_pending = True
        logger.debug(f"""Exit order Placed to {self.instruction} {self.qty} {self.symbol}, 
                         order price: {self.exit_order_price}, order time:{self.exit_order_time}, 
                         order id: {self.exit_order_id}""")
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
                logger.debug(
                    f"Entry order Filled to {self.instruction} {self.symbol}, price: {self.entry_price},"
                    f" qty:{self.qty}, time:{self.entry_time}")
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
            if exec_order_id == str(self.exit_order_id):
                self.exit_price = exec_order['exec_avg_price']
                self.exit_time = exec_order['exec_time']
                self.exit_order_status = 'FILLED'
                self.position_status = 'CLOSED'
                self.bought, self.sold = False, False
                self.exit_order_filled = True
                self.entered = False
                self.exit_pending = False
                self.client.open_stocks_limit += 1
                logger.debug(f"""Exit order Filled to {self.instruction} {self.qty} {self.symbol}, 
                                 price: {self.exit_price}, time:{self.exit_time}, order id: {self.exit_order_id}""")
                exit_data = self.save_trade(action='confirm_exit')
                self.messages.append(exit_data)
                self.trade_ended = True
                logger.debug(f'{self.symbol}: Trade completed, closing instance')
                return

        for order in self.client.orders:
            if str(order['order_id']) == str(self.exit_order_id) and order['status'] in ['Cancelled', 'Inactive']:
                order_status = order['status']
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
            message[action] = {'symbol': self.symbol, 'scan_name': self.scan_name, 'side': self.side,
                               'entry_order_time': self.entry_order_time,
                               'entry_order_price': self.entry_order_price, 'instruction': self.instruction,
                               'entry_order_id': self.entry_order_id, 'entry_order_status': self.entry_order_status,
                               'quantity': self.qty, 'trade_id': self.trade_id, 'trading_mode': self.trading_mode,
                               'initial_change': self.initial_change, 'rsi_period': self.rsi_period,
                               'rsi': float(self.rsi), 'average_volume_period': self.average_volume_period,
                               'avg_volume': float(self.avg_vol), 'volume': int(self.total_vol), 'rank': self.rank,
                               'long_sma_period': self.long_sma_period, 'long_sma': float(self.long_sma),
                               'short_sma_period': self.short_sma_period, 'short_sma': float(self.short_sma)}
            return message

        elif action == 'confirm_entry':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'entry_time': self.entry_time,
                               'entry_price': self.entry_price,
                               'entry_order_status': self.entry_order_status, 'position_status': self.position_status}
            return message

        elif action == 'make_exit':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'instruction': self.instruction,
                               'exit_order_id': self.exit_order_id, 'exit_order_time': self.exit_order_time,
                               'exit_order_price': self.exit_order_price,
                               'exit_order_status': self.exit_order_status}
            return message

        elif action == 'confirm_exit':
            message[action] = {'symbol': self.symbol, 'trade_id': self.trade_id, 'exit_time': self.exit_time,
                               'exit_price': self.exit_price, 'exit_type': self.exit_type,
                               'exit_order_status': self.exit_order_status, 'position_status': self.position_status}
            return message
