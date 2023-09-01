import warnings

import pandas as pd

from back_test.utils import relative_strength_index
from back_test.settings import logger

warnings.filterwarnings('ignore')


class MomentumBackTest:
    def __init__(self, client, symbol, start_date, end_date, rsi_period, gap_percent, price_limit,
                 rsi_lower_threshold, rsi_higher_threshold, volume_period, volume_multiplier, stop_loss, target,
                 pos_limit, extended_hours_data, benchmark_df):
        self.client = client
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.rsi_period = rsi_period
        self.gap_percent = gap_percent
        self.price_limit = price_limit
        self.rsi_lower_threshold = rsi_lower_threshold
        self.rsi_higher_threshold = rsi_higher_threshold
        self.volume_period = volume_period
        self.volume_multiplier = volume_multiplier
        self.stop_loss = stop_loss
        self.target = target
        self.pos_limit = pos_limit
        self.extended_hours_data = extended_hours_data
        self.benchmark_df = benchmark_df

        self.entered = False
        self.instruction = None
        self.bought = False
        self.sold = False
        self.entry_time = None
        self.entry_price = None
        self.qty = None
        self.sl = None
        self.tr = None
        self.exit_type = None
        self.exit_time = None
        self.exit_price = None
        self.today_date = None

        self.result_fields = ['symbol', 'instruction', 'entry_time', 'entry_price', 'qty', 'sl', 'tr', 'exit_type',
                              'exit_time', 'exit_price']
        self.records = pd.DataFrame(columns=self.result_fields)
        logger.debug(f"""Back test instance successfully started, symbol: {self.symbol}, start date: {self.start_date}, 
                         end date: {self.end_date}""")

    def handle_data(self):
        df = self.client.get_past_data(symbol=self.symbol, start_time=self.start_date, end_time=self.end_date,
                                       extended_hours=self.extended_hours_data)
        if df is None or not len(df):
            logger.debug(f'{self.symbol}: No data found')
            return
        df = df.join(self.benchmark_df, rsuffix='_b')
        del df['volume_b']
        return df

    def run(self):
        df = self.handle_data()
        if df is None or not len(df):
            return
        for i in range(len(df) - 1):
            ltp = df['close'].iloc[i]
            ltp_time = df.index[i]
            _high = df['high'].iloc[i]
            _low = df['low'].iloc[i]
            if self.today_date is None or self.today_date != ltp_time.date():
                self.today_date = ltp_time.date()
                logger.debug(f'{self.symbol}: Running back test for date: {self.today_date}')
            if self.entered:
                if self.bought and (_high >= self.tr or _low <= self.sl):
                    price = self.tr if _high >= self.tr else self.sl
                    self.exit_type = 'SL' if price == self.sl else 'TR'
                    self.handle_position(price=price, trade_time=ltp_time, purpose='exit')
                elif self.sold and (_low <= self.tr or _high >= self.sl):
                    price = self.tr if _low <= self.tr else self.sl
                    self.exit_type = 'SL' if price == self.sl else 'TR'
                    self.handle_position(price=price, trade_time=ltp_time, purpose='exit')
                else:
                    continue
            if ltp > self.price_limit:
                continue

            daily = df[:i + 1].resample('D').agg({'open': 'first', 'close': 'last', 'volume': 'sum',
                                                  'close_b': 'last'}).dropna()
            if len(daily) <= max(2, self.rsi_period, self.volume_period):
                continue
            cur_open = daily['open'].iloc[-1]
            prev_close = daily['close'].iloc[-2]
            change = ((ltp - prev_close) / prev_close) * 100
            bm_change = ((daily['close_b'].iloc[-1] - daily['close_b'].iloc[-2]) / daily['close_b'].iloc[-2]) * 100
            gap_percent = ((cur_open - prev_close) / prev_close) * 100
            daily['avg_vol'] = daily['volume'].rolling(window=self.volume_period).mean()
            volume = daily['volume'].iloc[-1]
            avg_vol = daily['avg_vol'].iloc[-1]
            relative_strength_index(daily, rsi_period=self.rsi_period)
            rsi = daily['rsi'].iloc[-1]
            # print(self.symbol, volume, rsi, avg_vol, ltp, ltp_time, change, bm_change, gap_percent)
            if change > max(0, bm_change) and gap_percent >= self.gap_percent and \
                    volume >= (avg_vol * self.volume_multiplier) and rsi >= self.rsi_higher_threshold:
                self.instruction = 'BUY'
                self.bought = True
                self.entered = True
                self.handle_position(price=ltp, trade_time=ltp_time, purpose='entry')
            elif change < min(0, bm_change) and gap_percent <= -self.gap_percent and \
                    volume >= (avg_vol * self.volume_multiplier) and rsi <= self.rsi_lower_threshold:
                self.instruction = 'SELL'
                self.sold = True
                self.entered = True
                self.handle_position(price=ltp, trade_time=ltp_time, purpose='entry')

        return self.records

    def handle_position(self, price, trade_time, purpose):
        if purpose == 'entry':
            self.entry_price = price
            self.entry_time = trade_time
            self.qty = int(self.pos_limit / price)
            if self.qty <= 0:
                logger.debug(f'{self.symbol}: qty is {self.qty}, it must be greater than 0 so increase position limit')
                self.entered, self.bought, self.sold = False, False, False
                return
            if self.bought:
                self.sl = self.entry_price * (1 - (self.stop_loss / 100))
                self.tr = self.entry_price * (1 + (self.target / 100))
            else:
                self.sl = self.entry_price * (1 + (self.stop_loss / 100))
                self.tr = self.entry_price * (1 - (self.target / 100))
            logger.info(f"""{self.symbol}: {self.instruction} position created, entry price: {self.entry_price}, 
                         entry time: {self.entry_time}, qty: {self.qty}, sl: {self.sl}, tr: {self.tr}""")
        else:
            self.entered, self.bought, self.sold = False, False, False
            self.exit_price = price
            self.exit_time = trade_time
            logger.info(f"""{self.symbol}: {self.instruction} position exited, exit type: {self.exit_type}, 
                         exit price: {self.exit_price}, exit time: {self.exit_time}""")
            self.update_records()

    def update_records(self):
        pos_result = {i: getattr(self, i) for i in self.result_fields}
        self.records = self.records.append(pos_result, ignore_index=True)
