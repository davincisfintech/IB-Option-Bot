import numpy as np
import pandas as pd

from new_back_test.settings import logger
from new_back_test.indicators import super_trend, exponential_moving_average


class BackTest:
    def __init__(self, client, unique_id, symbol, stop_loss, trailing_stop_loss, pos_limit, st_period, st_multiplier,
                 ema_period, price_diff):
        self.unique_id = unique_id
        self.symbol = symbol
        self.stop_loss = stop_loss
        self.client = client
        self.pos_limit = pos_limit
        self.trailing_stop_loss = trailing_stop_loss
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.ema_period = ema_period
        self.price_diff = price_diff

        self.start_price = None
        self.entered = False
        self.bought = False
        self.sold = False
        self.side = None
        self.entry_price = None
        self.entry_time = None
        self.qty = None
        self.initial_sl = None
        self.final_sl = None
        self.exit_time = None
        self.exit_price = None
        self.exit_type = None
        self.today_date = None

        self.result_fields = ['symbol', 'side', 'entry_time', 'entry_price', 'qty', 'initial_sl', 'final_sl',
                              'exit_type', 'exit_time', 'exit_price']
        self.records = pd.DataFrame(columns=self.result_fields)
        logger.debug(f"""{self.symbol}: Back test instance successfully started, unique id: {self.unique_id}""")

    def strategy_super_trend(self, df):
        exponential_moving_average(df, base='close', period=self.ema_period, target='ema')
        st_column_name = f'st_{self.st_period}_{self.st_multiplier}'
        st_dir_column_name = f'stx_{self.st_period}_{self.st_multiplier}'
        super_trend(df, period=self.st_period, multiplier=self.st_multiplier, sp_val=st_column_name,
                    sp_dir=st_dir_column_name)
        self.price_diff = df['close'].iloc[-1] * (self.price_diff / 100)
        long = (df[st_dir_column_name] == 'up') & ((df.low - df[st_column_name]) < self.price_diff) & (
                df.close > df.ema)
        short = (df[st_dir_column_name] == 'down') & ((df[st_column_name] - df.high) < self.price_diff) & (
                df.close < df.ema)
        long_close = df[st_dir_column_name] == 'down'
        short_close = df[st_dir_column_name] == 'up'
        conditions = [long, short, long_close, short_close]
        choices = ['long', 'short', 'long_close', 'short_close']

        df['signal'] = np.select(conditions, choices, default=np.nan)

    def run(self):
        while not len(self.client.data_frames[self.unique_id]):
            pass
        df = self.client.data_frames[self.unique_id]
        self.strategy_super_trend(df)
        logger.info(f'{self.symbol}: Data fetched, Running back test')
        start_point = max(self.st_period, self.ema_period) * 5
        for i in range(start_point, len(df)):
            if self.today_date is None or self.today_date != df.index[i].date():
                self.today_date = df.index[i].date()
                logger.debug(f'{self.symbol}: Running back test for date: {self.today_date}')

            candle_time = df.index[i]
            signal = df['signal'].iloc[i - 1]
            max_price = df['high'].iloc[i]
            min_price = df['low'].iloc[i]
            _open = df['open'].iloc[i]

            if not self.entered:
                if signal == 'long':
                    self.bought = True
                    self.side = 'BUY'
                    self.make_entry(entry_time=candle_time, entry_price=_open)

                elif signal == 'short':
                    self.sold = True
                    self.side = 'SELL'
                    self.make_entry(entry_time=candle_time, entry_price=_open)

            if self.entered:
                exit_type, exit_price = None, None
                if (self.bought and signal in ['short', 'long_close']) or \
                        (self.sold and signal in ['long', 'short_close']):
                    exit_type = 'Super trend signal'
                    exit_price = _open

                elif (self.bought and min_price < self.final_sl) or (self.sold and max_price > self.final_sl):
                    if self.bought:
                        exit_price = _open if _open < self.final_sl else self.final_sl
                    else:
                        exit_price = _open if _open > self.final_sl else self.final_sl
                    exit_type = 'SL'

                if exit_price:
                    self.make_exit(exit_time=candle_time, exit_type=exit_type, exit_price=exit_price)

                if self.trailing_stop_loss and ((self.bought and max_price > self.start_price) or
                                                (self.sold and min_price < self.start_price)):
                    before_sl = self.final_sl
                    reference_price = self.start_price
                    if self.bought:
                        self.final_sl = self.final_sl + (max_price - self.start_price)
                        self.start_price = max_price
                    else:
                        self.final_sl = self.final_sl - (self.start_price - min_price)
                        self.start_price = min_price
                    logger.info(
                        f'{self.symbol}: for {self.side} position SL trailed from {before_sl} to {self.final_sl}, '
                        f'time: {df.index[i]}, price changed from: {reference_price} to {self.start_price}')

        return self.records

    def make_entry(self, entry_time, entry_price):
        self.qty = self.pos_limit / entry_price
        if self.qty <= 0:
            logger.debug(f'{self.symbol}: Qty: {self.qty} is less 0, please increase position limit')
            return
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.entered = True
        if self.bought:
            self.initial_sl = self.final_sl = self.entry_price * (1 - (self.stop_loss / 100))
        else:
            self.initial_sl = self.final_sl = self.entry_price * (1 + (self.stop_loss / 100))
        self.start_price = self.entry_price

        logger.info(f"""{self.symbol}: Entry {self.side} position created at time: {self.entry_time}, 
                        price: {self.entry_price}, quantity: {self.qty}, stop loss: {self.initial_sl}, 
                        total entry value: {self.entry_price * self.qty}""")

    def make_exit(self, exit_time, exit_type, exit_price):
        self.exit_time = exit_time
        self.exit_type = exit_type
        self.exit_price = exit_price
        exit_value = self.qty * self.exit_price
        entry_value = self.qty * self.entry_price
        gross = exit_value - entry_value if self.bought else entry_value - exit_value
        logger.info(f"""{self.symbol}: {self.side} Position exited at time: {self.exit_time}, price: {self.exit_price}, 
                        exit type: {self.exit_type}, 
                        exit value: {exit_value}, entry value: {entry_value}, total gross profit: {gross}""")

        self.entered, self.bought, self.sold = False, False, False
        self.update_records()

    def update_records(self):
        pos_result = {i: getattr(self, i) for i in self.result_fields}
        self.records = self.records.append(pos_result, ignore_index=True)
