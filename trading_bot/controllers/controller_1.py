from datetime import datetime
from threading import Thread
from time import sleep

from ibapi.client import ExecutionFilter

from trading_bot.clients.ib_client import IBapi
from trading_bot.database.db import ScannedData
from trading_bot.scrappers.benzinga import BenzingaScraper
from trading_bot.screeners.momentum_screener import MomentumScreener
from trading_bot.settings import logger, TZ
from trading_bot.trade_managers.tv_trade_manager import TvTradeManager


class Controller:
    def __init__(self, client, scrapper, screener, trading_mode, order_type, position_limit):
        self.client = client
        self.scrapper = scrapper
        self.screener = screener
        self.trading_mode = trading_mode.upper()
        self.order_type = order_type.upper()
        self.position_limit = position_limit
        self.symbols_received = []
        self.symbols_passed_screener = []

    def run_screening_instance(self, args):
        obj, symbol, news = args
        logger.info(f"{symbol}: Screening...")
        filtered_data = self.screener.filter(symbol=symbol)
        if filtered_data is None:
            return
        symbol, price, gap_percent, volume, rsi = filtered_data
        logger.info(f'{symbol}: Passed screener...')
        self.symbols_passed_screener.append(symbol)

        obj = ScannedData(symbol=symbol, scan_time=datetime.now(tz=TZ), price=price, volume=volume,
                          gap_percent=gap_percent, rsi=rsi, news_title=news)
        obj.save_to_db()
        logger.debug(f'{symbol}: Screened data Saved')
        return symbol, price

    def run_trading_instance(self, args):
        symbol, price = args
        # Initialize Trade manager
        contract = self.client.make_contract(symbol, 'STK', 'SMART', 'ISLAND')
        trading_bot = TvTradeManager(self.client, trading_mode=self.trading_mode,
                                     contract=contract, pos_limit=self.position_limit,
                                     instruction='BUY', order_type=self.order_type,
                                     price=price)
        # Make trade
        response = trading_bot.trade()
        if response is True:
            logger.debug(f'{symbol}: Successfully completed trade')
        else:
            logger.debug(f'{symbol}: Error completing trade')

    def run(self):
        if not self.scrapper.data_queue.empty():
            data = self.scrapper.data_queue.get()
            self.symbols_received.extend([i['symbol'] for i in data])
        else:
            data = []

        # Run screener instances
        screener_instances = [(self.screener, i['symbol'], i['news']) for i in data]
        # with ThreadPoolExecutor() as executor:
        #     res = executor.map(self.run_screening_instance, screener_instances)

        # filtered_symbols = [r for r in res if r is not None]
        filtered_symbols = []
        for s in screener_instances:
            res = self.run_screening_instance(s)
            if res is not None:
                filtered_symbols.append(res)

        if len(filtered_symbols):
            logger.info(f'Total symbols received: {len(self.symbols_received)}, {self.symbols_received},\n'
                        f'symbols passed screener: {len(self.symbols_passed_screener)}, {self.symbols_passed_screener},\n'
                        f'screener pass rate: {(len(self.symbols_passed_screener) / len(self.symbols_received)) * 100}')
        # with ThreadPoolExecutor() as executor:
        #     res = executor.map(self.run_trading_instance, filtered_symbols)
        #     res = [r for r in res if r is not None]
        #     return res

        for f in filtered_symbols:
            self.run_trading_instance(f)


def run(rsi_period, gap_percent, price_limit, rsi_threshold, volume_period, volume_multiplier,
        trading_mode='PAPER', order_type='MKT', position_limit=100):
    # Initialize IB client
    client = IBapi()
    socket_port = 7497 if trading_mode.lower() == 'paper' else 7496
    client.connect('127.0.0.1', socket_port, 123)
    client_thread = Thread(target=client.run, daemon=True)
    client_thread.start()
    sleep(3)
    client.reqPositions()
    client.reqAccountSummary(9002, "All", "$LEDGER")
    client.reqAllOpenOrders()
    client.reqExecutions(10001, ExecutionFilter())
    while not client.total_amount:
        pass

    sleep(1)
    logger.info('IB client started')

    scrapper = BenzingaScraper()
    scrapper.start_streaming()
    logger.info('Benzinga Scrapper Started')

    screener = MomentumScreener(rsi_period=rsi_period, gap_percent=gap_percent,
                                price_limit=price_limit, rsi_threshold=rsi_threshold,
                                volume_period=volume_period, volume_multiplier=volume_multiplier)
    logger.info('Momentum Screener Initialized')

    controller = Controller(client=client, scrapper=scrapper, screener=screener, trading_mode=trading_mode,
                            order_type=order_type, position_limit=position_limit)
    logger.info('Running...')
    while True:
        controller.run()
