from datetime import datetime

from trading_bot.database.db import ScannedData
from trading_bot.scrappers.benzinga import BenzingaScraper
from trading_bot.screeners.momentum_screener import MomentumScreener
from trading_bot.settings import logger, TZ

# Screening parameters
rsi_period = 14  # Period for calculating RSI
gap_percent = -5  # Minimum Gap up percent
price_limit = 2000  # Price condition. i.e. only select stocks priced less than this
rsi_threshold = 50  # RSI threshold. i.e. RSI should be greater than tis
volume_period = 5  # Volume period. i.e. Number of days to consider for average volume calculation
volume_multiplier = 2  # Volume multiplier. i.e. Volume must be greater than avg_volume * volume_multiplier

bz = BenzingaScraper()
bz.start_streaming()
logger.info('Scrapper+Screener Started')

symbols_received = []
symbols_passed_screener = []

while True:
    if not bz.data_queue.empty():
        data = bz.data_queue.get()
        symbols_received.extend([i['symbol'] for i in data])
    else:
        data = []

    for i in data:
        symbol = i['symbol']
        news = i['news']
        screener = MomentumScreener(rsi_period=rsi_period, gap_percent=gap_percent, price_limit=price_limit,
                                    rsi_threshold=rsi_threshold, volume_period=volume_period,
                                    volume_multiplier=volume_multiplier)
        filtered_data = screener.filter(symbol=symbol)
        if filtered_data is None:
            continue
        symbol, price, gap_percent, volume, rsi = filtered_data
        logger.info(f'{symbol}: Passed screener...')
        symbols_passed_screener.append(symbol)

        obj = ScannedData(symbol=symbol, scan_time=datetime.now(tz=TZ), price=price, volume=volume,
                          gap_percent=gap_percent, rsi=rsi, news_title=news)
        obj.save_to_db()
        logger.debug(f'{symbol}: Screened data Saved')
        logger.info(f"""Total symbols received: {len(symbols_received)}, {symbols_received}, 
                        symbols passed screener: {len(symbols_passed_screener)}, {symbols_passed_screener}, 
                        screener pass rate: {(len(symbols_passed_screener) / len(symbols_received)) * 100}""")
