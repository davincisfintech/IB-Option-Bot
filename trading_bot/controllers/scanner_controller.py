import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from ibapi.client import ExecutionFilter

from trading_bot.clients.ib_client import IBapi
from trading_bot.database.db import engine, session, ScannerTradesData, ScannersSourceData
from trading_bot.database.db_handler import save_scan_bot_trade
from trading_bot.settings import logger, TZ
from trading_bot.scrappers.benzinga import BenzingaScraper
from trading_bot.scrappers.blackboxstocks import BlackBoxStocksScraper
from trading_bot.trade_managers.scanner_trade_manager import TradeManager


class Controller:
    def __init__(self, client, trade_managers, pos_limit, top_gainers_id, top_losers_id, hot_by_volume_id,
                 benzinga_scrapper, bbs_scrapper, trade_args):
        self.client = client
        self.trade_managers = trade_managers
        self.benzinga_scrapper = benzinga_scrapper
        self.bbs_scrapper = bbs_scrapper
        self.pos_limit = pos_limit
        self.trade_args = trade_args
        self.top_gainers_id = top_gainers_id
        self.top_losers_id = top_losers_id
        self.hot_by_volume_id = hot_by_volume_id
        self.benzinga_scraper_symbols_received = []
        self.bbs_scraper_symbols_received = []

    def create_trading_instance(self, unq_id, contract, rank, instruction, scan_name):
        if contract.symbol not in self.benzinga_scraper_symbols_received or \
                contract.symbol not in self.bbs_scraper_symbols_received:
            return
        source_1 = 'Benzinga' if contract.symbol in self.benzinga_scraper_symbols_received else 'BlackBox'
        if contract.symbol in self.trade_managers:
            initial_side = self.trade_managers[contract.symbol].side
            initial_scan_name = self.trade_managers[contract.symbol].scan_name
            if scan_name in ['TOP_GAINERS', 'TOP_LOSERS'] and initial_scan_name in ['TOP_GAINERS', 'TOP_LOSERS']:
                if initial_scan_name != scan_name:
                    self.trade_managers[contract.symbol].side = instruction
                    self.trade_managers[contract.symbol].scan_name = scan_name
                    logger.debug(f'{contract.symbol} Side changed from {initial_side} to {instruction}')
                initial_rank = self.trade_managers[contract.symbol].rank
                if rank != initial_rank:
                    self.trade_managers[contract.symbol].rank = rank
                    # logger.debug(f'{contract.symbol} Rank changed from {initial_rank} to {rank}')
                return
            elif scan_name == 'HOT_BY_VOLUME' and initial_scan_name == 'HOT_BY_VOLUME':
                initial_rank = self.trade_managers[contract.symbol].rank
                if rank != initial_rank:
                    self.trade_managers[contract.symbol].rank = rank
                    # logger.debug(f'{contract.symbol}: scan name: {scan_name} '
                    #              f'Rank changed from {initial_rank} to {rank}')
                return
            else:
                return

        obj = ScannersSourceData(symbol=contract.symbol, scan_time=datetime.now(tz=TZ), source_1=source_1,
                                 source_2='IB', scan_type=scan_name, rank=rank)
        obj.save_to_db()
        logger.debug(f'{contract.symbol}: Scanned data Saved')

        pos_limit = self.client.total_amount * (self.pos_limit / 100)
        self.client.reqHistoricalData(unq_id, contract, '', f'2 D', '1 min', 'TRADES', 0, 2, True, [])

        # Initialize Trade manager
        trade_obj = TradeManager(client=self.client, unique_id=unq_id, contract=contract, pos_limit=pos_limit,
                                 rank=rank, instruction=instruction, side=instruction, scan_name=scan_name,
                                 **self.trade_args)
        self.trade_managers[trade_obj.symbol] = trade_obj

    @staticmethod
    def run_trading_instance(obj):
        return obj.trade()

    def run(self):
        if self.benzinga_scrapper is not None and not self.benzinga_scrapper.data_queue.empty():
            data = self.benzinga_scrapper.data_queue.get()
            symbols = [i['symbol'] for i in data]
            self.benzinga_scraper_symbols_received.extend(symbols)
            logger.info(f'Benzinga symbols received: {symbols}')

        if not self.bbs_scrapper.data_queue.empty():
            data = self.bbs_scrapper.data_queue.get()
            symbols = [i['symbol'] for i in data]
            self.bbs_scraper_symbols_received.extend(symbols)
            logger.info(f'Black Box symbols received: {symbols}')

        scanned_contracts = self.client.scanned_contracts
        if not len(scanned_contracts):
            return
        i = self.client.nextorderId
        top_gainers, top_losers, hot_by_volume = [], [], []
        if self.top_gainers_id in scanned_contracts:
            top_gainers = scanned_contracts[self.top_gainers_id]
        if self.top_losers_id in scanned_contracts:
            top_losers = scanned_contracts[self.top_losers_id]
        if self.hot_by_volume_id in scanned_contracts:
            hot_by_volume = scanned_contracts[self.hot_by_volume_id]
        for i, s in enumerate(top_gainers, start=self.client.nextorderId):
            self.create_trading_instance(unq_id=i, rank=s, instruction='BUY', contract=top_gainers[s],
                                         scan_name='TOP_GAINERS')

        self.client.nextorderId = i + 1

        for i, s in enumerate(top_losers, start=self.client.nextorderId):
            self.create_trading_instance(unq_id=i, rank=s, instruction='SELL', contract=top_losers[s],
                                         scan_name='TOP_LOSERS')

        self.client.nextorderId = i + 1

        for i, s in enumerate(hot_by_volume, start=self.client.nextorderId):
            self.create_trading_instance(unq_id=i, rank=s, instruction=None, contract=hot_by_volume[s],
                                         scan_name='HOT_BY_VOLUME')

        self.client.nextorderId = i + 1

        max_workers = self.client.open_stocks_limit if self.client.open_stocks_limit > 0 else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            res = executor.map(self.run_trading_instance, list(self.trade_managers.values()))
        res = [r for r in res if r is not None]

        for r in res:
            # Store trade details if trade data received
            if isinstance(r, dict):
                if r['msg']:
                    for i in r['msg']:
                        if i:
                            for k, v in i.items():
                                save_scan_bot_trade(k, v)
            else:
                # Remove instance if trade is ended for it
                if r.trade_ended:
                    del self.trade_managers[r.symbol]
                    self.client.cancelHistoricalData(r.id)
                    logger.debug(f'{r.symbol} instance removed from trading manager')


def main(trading_mode, pos_limit, stock_limit, exit_percent, top_gainers_to_track, top_gainers_to_trade, above_price,
         below_price, above_volume, average_volume, market_cap_usd, rsi_period, rsi_upper_threshold,
         rsi_lower_threshold, average_volume_period, enable_benzinga,
         short_sma_period, long_sma_period, order_type='MKT', clear_open_orders_and_positions_from_db=False):
    if trading_mode.lower() not in ['live', 'paper']:
        logger.debug(f'Invalid trading mode: {trading_mode}, it must be either live or paper')
        return
    if order_type not in ['LMT', 'MKT']:
        logger.debug(f'Invalid order type: {order_type}, it must be either LMT or MKT')
        return
    if stock_limit < 1:
        logger.debug('Make sure its greater than or equal to 1')
        return
    if clear_open_orders_and_positions_from_db:
        session.query(ScannerTradesData).filter(ScannerTradesData.trading_mode == trading_mode.capitalize()).filter(
            (ScannerTradesData.position_status == 'OPEN') | (ScannerTradesData.entry_order_status == 'OPEN')).delete()
        session.commit()
        logger.debug('Cleared open orders and positions from database')
    open_pos_stock_list = pd.read_sql('scanner_trades_data', engine)
    mask = (open_pos_stock_list['trading_mode'].str.upper() == trading_mode.upper()) & (
            (open_pos_stock_list['position_status'] == "OPEN") | (
            open_pos_stock_list['entry_order_status'] == 'OPEN'))
    open_pos_stock_list = open_pos_stock_list[mask]
    open_pos_stock_list = list(open_pos_stock_list.T.to_dict().values())
    open_pos_symbols = {s['symbol']: s for s in open_pos_stock_list}

    client = IBapi()
    socket_port = 7497 if trading_mode.lower() == 'paper' else 7496
    client.connect('127.0.0.1', socket_port, 123)

    client_thread = threading.Thread(target=client.run, daemon=True)
    client_thread.start()

    time.sleep(3)
    client.reqPositions()
    client.reqAccountSummary(9002, "All", "$LEDGER")
    client.reqAllOpenOrders()
    client.reqExecutions(10001, ExecutionFilter())
    top_gainers_id = 5001  # client.nextorderId
    scan_sub = client.get_sub(scan_name="TOP_PERC_GAIN", above_price=above_price, below_price=below_price,
                              above_volume=above_volume, average_volume=average_volume, market_cap_usd=market_cap_usd,
                              limit=top_gainers_to_track)
    client.reqScannerSubscription(top_gainers_id, scan_sub, [], [])
    client.nextorderId += 1

    top_losers_id = 5002  # client.nextorderId
    scan_sub = client.get_sub(scan_name="TOP_PERC_LOSE", above_price=above_price, below_price=below_price,
                              above_volume=above_volume, average_volume=average_volume, market_cap_usd=market_cap_usd,
                              limit=top_gainers_to_track)
    client.reqScannerSubscription(top_losers_id, scan_sub, [], [])
    client.nextorderId += 1

    hot_by_volume_id = 5003  # client.nextorderId
    scan_sub = client.get_sub(scan_name="HOT_BY_VOLUME", above_price=above_price, below_price=below_price,
                              above_volume=above_volume, average_volume=average_volume, market_cap_usd=market_cap_usd,
                              limit=top_gainers_to_track)
    client.reqScannerSubscription(hot_by_volume_id, scan_sub, [], [])
    client.nextorderId += 1

    while not client.total_amount:
        pass

    client.open_stocks_limit = stock_limit

    time.sleep(1)
    logger.info('IB client started')

    if enable_benzinga:
        benzinga_scrapper = BenzingaScraper()
        benzinga_scrapper.start_streaming()
        logger.info('Benzinga Scrapper Started')
    else:
        benzinga_scrapper = None

    bbs_scrapper = BlackBoxStocksScraper()
    bbs_scrapper.start_streaming()
    logger.info('Black Box Scrapper Started')

    trade_managers = dict()

    trade_args = {'trading_mode': trading_mode, 'entry_order_type': order_type, 'exit_percent': exit_percent,
                  'top_gainers_to_trade': top_gainers_to_trade, 'rsi_period': rsi_period,
                  'average_volume': average_volume, 'rsi_upper_threshold': rsi_upper_threshold,
                  'rsi_lower_threshold': rsi_lower_threshold,
                  'average_volume_period': average_volume_period, 'short_sma_period': short_sma_period,
                  'long_sma_period': long_sma_period, 'above_volume': above_volume}

    for i, s in enumerate(open_pos_symbols, start=client.nextorderId):
        logger.info(f'open position/order found in {s}, reading parameters...')
        contract = client.make_contract(s, 'STK', 'SMART', 'ISLAND')
        kwargs = {'client': client, 'unique_id': i, 'contract': contract,
                  'pos_limit': client.total_amount * (pos_limit / 100), **trade_args}

        trade = open_pos_symbols[s]
        entry_order_filled = True if trade['entry_order_status'] == 'FILLED' else False
        exit_pending = True if trade['exit_order_status'] == 'OPEN' else False
        bought = True if trade['side'] == 'BUY' else False
        sold = True if trade['side'] == 'SELL' else False
        extra_args = {'entered': True, 'entry_order_filled': entry_order_filled,
                      'bought': bought, 'sold': sold, 'rank': trade['rank'],
                      'instruction': trade['instruction'], 'qty': trade['quantity'],
                      'entry_order_id': trade['entry_order_id'], 'exit_order_id': trade['exit_order_id'],
                      'exit_pending': exit_pending, 'entry_order_price': trade['entry_order_price'],
                      'trade_id': trade['trade_id'], 'exit_order_price': trade['exit_order_price'],
                      'initial_change': trade['initial_change'], 'side': trade['side'], 'scan_name': trade['scan_name']}
        client.open_stocks_limit -= 1

        kwargs.update(extra_args)

        trade_managers[s] = TradeManager(**kwargs)
        client.reqHistoricalData(i, contract, '', f'2 D', '1 min', 'TRADES', 0, 2, True, [])

    controller = Controller(client=client, trade_managers=trade_managers, benzinga_scrapper=benzinga_scrapper,
                            bbs_scrapper=bbs_scrapper, pos_limit=pos_limit,
                            top_gainers_id=top_gainers_id, top_losers_id=top_losers_id,
                            hot_by_volume_id=hot_by_volume_id, trade_args=trade_args)
    logger.debug('Bot Running...')
    while True:
        controller.run()
