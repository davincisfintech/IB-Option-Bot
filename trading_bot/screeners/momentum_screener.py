from datetime import datetime, timedelta

import investpy

from trading_bot.settings import logger, TZ


class MomentumScreener:
    def __init__(self, rsi_period, gap_percent, price_limit, rsi_lower_threshold, rsi_higher_threshold, volume_period,
                 volume_multiplier):
        self.rsi_period = rsi_period
        self.gap_percent = gap_percent
        self.price_limit = price_limit
        self.rsi_lower_threshold = rsi_lower_threshold
        self.rsi_higher_threshold = rsi_higher_threshold
        self.volume_period = volume_period
        self.volume_multiplier = volume_multiplier
        self.instruction = None

    def get_data(self, symbol):
        logger.info(f'{symbol}: Fetching data...')
        days_before = max(self.volume_period, self.rsi_period) + 200
        from_date = datetime.strftime(datetime.now(tz=TZ) - timedelta(days=days_before), '%d/%m/%Y')
        to_date = datetime.strftime(datetime.now(tz=TZ), '%d/%m/%Y')
        try:
            df = investpy.get_stock_historical_data(stock=symbol,
                                                    country='United States',
                                                    from_date=from_date,
                                                    to_date=to_date, as_json=False)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            logger.exception(e)
            return

        df.columns = ['open', 'high', 'low', 'close', 'volume']
        logger.info(f'{symbol}: Data fetched')
        return df

    def rsi(self, df, base="close"):
        delta = df[base].diff()
        up, down = delta.copy(), delta.copy()

        up[up < 0] = 0
        down[down > 0] = 0

        r_up = up.ewm(com=self.rsi_period - 1, adjust=False).mean()
        r_down = down.ewm(com=self.rsi_period - 1, adjust=False).mean().abs()

        df['rsi'] = 100 - 100 / (1 + r_up / r_down)
        df['rsi'].fillna(0, inplace=True)

    def filter(self, symbol, benchmark_change):
        df = self.get_data(symbol=symbol)
        if df is None or not len(df) > 1:
            logger.info(f'{symbol}: Error getting data')
            return
        logger.info(f'{symbol}: Running screener...')
        price = df['close'].iloc[-1]
        logger.info(f'{symbol}: Price: {price}, price condition limit: {self.price_limit}')
        if not price <= self.price_limit:
            logger.info(f'{symbol}: Price limit condition not matched')
            return
        logger.info(f'{symbol}: Price limit condition matched')
        cur_open = df['open'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        cur_close = df['close'].iloc[-1]
        change = ((cur_close - prev_close) / prev_close) * 100
        logger.info(f'{symbol}: Day change(%): {change}, benchmark change: {benchmark_change}')
        if change > 0 and change > benchmark_change:
            self.instruction = 'BUY'
        elif change < 0 and change < benchmark_change:
            self.instruction = 'SELL'
        else:
            logger.info(f'{symbol}: Price change and benchmark change comparison condition not matched')
            return
        gap_percent = ((cur_open - prev_close) / prev_close) * 100
        logger.info(f'{symbol}: Price gap: {gap_percent}, gap condition percent: {self.gap_percent}')
        if self.instruction == 'BUY' and gap_percent >= self.gap_percent:
            self.instruction = 'BUY'
        elif self.instruction == 'SELL' and gap_percent <= -self.gap_percent:
            self.instruction = 'SELL'
        else:
            logger.info(f'{symbol}: Price gap condition not matched for {self.instruction} signal')
            return
        logger.info(f'{symbol}: Price gap {self.instruction} condition matched')
        df['avg_vol'] = df['volume'].rolling(window=self.volume_period).mean()
        volume = df['volume'].iloc[-1]
        avg_vol = df['avg_vol'].iloc[-1]
        logger.info(f'{symbol}: Volume: {volume}, {self.volume_period} day average volume: {avg_vol}, '
                    f'volume multiplier: {self.volume_multiplier}')
        if not volume >= (avg_vol * self.volume_multiplier):
            logger.info(f'{symbol}: Volume condition not matched')
            return
        logger.info(f'{symbol}: Volume condition matched')
        self.rsi(df)
        rsi = df['rsi'].iloc[-1]
        logger.info(f'{symbol}: RSI: {rsi}, rsi lower_threshold: {self.rsi_lower_threshold}, '
                    f'rsi higher threshold: {self.rsi_higher_threshold}')
        if self.instruction == 'BUY' and rsi >= self.rsi_higher_threshold:
            self.instruction = 'BUY'
        elif self.instruction == 'SELL' and rsi <= self.rsi_lower_threshold:
            self.instruction = 'SELL'
        else:
            logger.info(f'{symbol}: RSI condition not matched for {self.instruction} signal')
            return
        logger.info(f'{symbol}: RSI {self.instruction} condition matched')
        return symbol, float(price), float(gap_percent), int(volume), float(rsi)
