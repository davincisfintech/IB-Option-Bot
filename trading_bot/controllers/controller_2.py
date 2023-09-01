import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import investpy
import pandas as pd
from ibapi.client import ExecutionFilter

from trading_bot.clients.ib_client import IBapi
from trading_bot.database.db import engine, session, TradesDataAll, ScannedData
from trading_bot.database.db_handler import save_trade
from trading_bot.scrappers.benzinga import BenzingaScraper
from trading_bot.screeners.momentum_screener import MomentumScreener
from trading_bot.settings import logger, TZ
from trading_bot.trade_managers.long_trade_manager import TradeManager


class Controller:
    def __init__(self, client, trade_managers, scrapper, screener, pos_limit, run_without_filter, trade_args):
        self.client = client
        self.trade_managers = trade_managers
        self.scrapper = scrapper
        self.screener = screener
        self.pos_limit = pos_limit
        self.run_without_filter = run_without_filter
        self.trade_args = trade_args
        self.symbols_received = []
        self.symbols_passed_screener = []

    def run_screening_instance(self, args, benchmark_change):
        obj, symbol, news = args
        logger.info(f"{symbol}: Screening...")
        filtered_data = self.screener.filter(symbol=symbol, benchmark_change=benchmark_change)
        if filtered_data is None:
            return
        symbol, price, gap_percent, volume, rsi = filtered_data
        instruction = self.screener.instruction
        logger.info(f'{symbol}: Passed screener on {instruction} side...')
        self.symbols_passed_screener.append(symbol)

        obj = ScannedData(symbol=symbol, scan_time=datetime.now(tz=TZ), price=price, volume=volume,
                          gap_percent=gap_percent, rsi=rsi, news_title=news)
        obj.save_to_db()
        logger.debug(f'{symbol}: Screened data Saved')
        return symbol, instruction, price

    def create_trading_instance(self, unq_id, args):
        symbol, instruction, price = args
        contract = self.client.make_contract(symbol, 'STK', 'SMART', 'ISLAND')
        pos_limit = self.client.total_amount * (self.pos_limit / 100)
        self.client.reqMktDepth(unq_id, contract, 5, True, [])
        self.client.reqTickByTickData(unq_id, contract, "AllLast", 0, False)

        # Initialize Trade manager
        trade_obj = TradeManager(client=self.client, unique_id=unq_id, contract=contract, pos_limit=pos_limit,
                                 ltp=price, instruction=instruction, **self.trade_args)
        self.trade_managers[trade_obj.symbol] = trade_obj

    @staticmethod
    def run_trading_instance(obj):
        return obj.trade()

    def run(self):
        if not self.scrapper.data_queue.empty():
            data = self.scrapper.data_queue.get()
            self.symbols_received.extend([i['symbol'] for i in data])
        else:
            data = []

        if not self.run_without_filter:
            # Run screener instances
            screener_instances = [(self.screener, i['symbol'], i['news']) for i in data]
            # with ThreadPoolExecutor() as executor:
            #     res = executor.map(self.run_screening_instance, screener_instances)

            # filtered_symbols = [r for r in res if r is not None]
            filtered_symbols = []
            benchmark_change = 0
            if len(screener_instances):
                res = investpy.get_index_recent_data(index='S&P 500', country='United States', order='asc')
                if res is not None and len(res) > 1:
                    benchmark_change = ((res['Close'].iloc[-1] - res['Close'].iloc[-2]) / res['Close'].iloc[-2]) * 100
                    logger.debug(f'Benchmark index S&P 500 change: {benchmark_change}')
                else:
                    screener_instances = []
            for s in screener_instances:
                res = self.run_screening_instance(s, benchmark_change)
                if res is not None:
                    filtered_symbols.append(res)

            if len(filtered_symbols):
                logger.info(f'Total symbols received: {len(self.symbols_received)}, {self.symbols_received},\n'
                            f'symbols passed screener: {len(self.symbols_passed_screener)}, {self.symbols_passed_screener},'
                            f'\n'
                            f'screener pass rate: {(len(self.symbols_passed_screener) / len(self.symbols_received)) * 100}')

            filtered_symbols = [f for f in filtered_symbols if f[0] not in self.trade_managers]

        else:
            filtered_symbols = [(i['symbol'], 'BUY', None) for i in data if i['symbol'] not in self.trade_managers]

        for i, s in enumerate(filtered_symbols, start=self.client.nextorderId):
            self.create_trading_instance(unq_id=i, args=s)

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
                                save_trade(k, v)
            else:
                # Remove instance if trade is ended for it
                if r.trade_ended:
                    del self.trade_managers[r.symbol]
                    logger.debug(f'{r.symbol} instance removed from trading manager')


def main(trading_mode, pos_limit, stop_loss, target, stock_limit, rsi_period, gap_percent, price_limit,
         rsi_lower_threshold, rsi_higher_threshold, volume_period, volume_multiplier, run_without_filter,
         order_type='MKT', clear_open_orders_and_positions_from_db=False):
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
        session.query(TradesDataAll).filter(TradesDataAll.trading_mode == trading_mode.capitalize()).filter(
            (TradesDataAll.position_status == 'OPEN') | (TradesDataAll.entry_order_status == 'OPEN')).delete()
        session.commit()
        logger.debug('Cleared open orders and positions from database')
    open_pos_stock_list = pd.read_sql('trades_data_all', engine)
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

    while not client.total_amount:
        pass

    client.open_stocks_limit = stock_limit

    time.sleep(1)
    logger.info('IB client started')

    trade_managers = dict()

    trade_args = {'trading_mode': trading_mode, 'target': target, 'stop_loss': stop_loss,
                  'entry_order_type': order_type}

    for i, s in enumerate(open_pos_symbols, start=client.nextorderId):
        logger.info(f'open position/order found in {s}, reading parameters...')
        contract = client.make_contract(s, 'STK', 'SMART', 'ISLAND')
        kwargs = {'client': client, 'unique_id': i, 'contract': contract,
                  'pos_limit': client.total_amount * (pos_limit / 100), **trade_args}

        trade = open_pos_symbols[s]
        entry_order_filled = True if trade['entry_order_status'] == 'FILLED' else False
        exit_pending = True if trade['sl_exit_order_status'] == 'OPEN' else False
        bought = True if trade['side'] == 'BUY' else False
        sold = True if trade['side'] == 'SELL' else False
        extra_args = {'entered': True, 'entry_order_filled': entry_order_filled,
                      'bought': bought, 'sold': sold,
                      'instruction': trade['instruction'], 'qty': trade['quantity'],
                      'entry_order_id': trade['entry_order_id'], 'sl_exit_order_id': trade['sl_exit_order_id'],
                      'tr_exit_order_id': trade['tr_exit_order_id'],
                      'sl': trade['stop_loss'], 'tr': trade['target'], 'exit_pending': exit_pending,
                      'entry_order_price': trade['entry_order_price'], 'trade_id': trade['trade_id'],
                      'sl_exit_order_price': trade['sl_exit_order_price'],
                      'tr_exit_order_price': trade['tr_exit_order_price']}
        client.open_stocks_limit -= 1

        kwargs.update(extra_args)

        trade_managers[s] = TradeManager(**kwargs)

    scrapper = BenzingaScraper()
    scrapper.start_streaming()
    logger.info('Benzinga Scrapper Started')

    screener = MomentumScreener(rsi_period=rsi_period, gap_percent=gap_percent,
                                price_limit=price_limit, rsi_lower_threshold=rsi_lower_threshold,
                                rsi_higher_threshold=rsi_higher_threshold,
                                volume_period=volume_period, volume_multiplier=volume_multiplier)
    logger.info('Momentum Screener Initialized')

    controller = Controller(client=client, trade_managers=trade_managers, scrapper=scrapper, screener=screener,
                            pos_limit=pos_limit, trade_args=trade_args, run_without_filter=run_without_filter)
    logger.debug('Bot Running...')
    while True:
        controller.run()
