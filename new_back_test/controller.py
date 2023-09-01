import threading
import time
import os
import signal
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from dateutil.parser import parse

from new_back_test.clients.ib import IBapi
from new_back_test.back_test import BackTest
from new_back_test.settings import RECORDS_DIR, logger, TZ
from new_back_test.utils import calc_columns, calc_metrics


class Controller:
    def __init__(self, bt_instances, charge, output_file):
        self.bt_instances = bt_instances
        self.charge = charge
        self.output_file = output_file

    @staticmethod
    def run_instance(obj):
        return obj.run()

    def run(self):
        logger.debug('Running Back test...')
        with ThreadPoolExecutor() as executor:
            res = executor.map(self.run_instance, self.bt_instances)
        res = [r for r in res if r is not None]
        if not len(res):
            logger.debug('No Results Found')
            return
        df = pd.concat(res, axis=0)
        if not len(df):
            logger.debug('No Results Found')
            return
        logger.debug('Backtest done, exporting results to excel...')
        if not os.path.exists(RECORDS_DIR):
            os.mkdir(RECORDS_DIR)
        file = RECORDS_DIR / f'{self.output_file}_{datetime.now(tz=TZ)}.xlsx'.replace(' ', '_').replace(':', '_')
        df, records = calc_columns(df, charge=self.charge)
        metrics = calc_metrics(df)
        with pd.ExcelWriter(file) as writer:
            records.to_excel(writer, sheet_name='Trades', index=False)
            metrics.to_excel(writer, sheet_name='Metrics')
        logger.debug(f'Done, check {file} for results')


def run(account_mode, symbols, stop_loss, trailing_stop_loss, st_period, st_multiplier, ema_period, price_diff,
        start_date, end_date, time_frame, pos_limit, charges, only_regular_session_data, what_type, output_file):
    symbols = list(set([s.strip().upper() for s in symbols]))
    st_period, st_multiplier, ema_period = int(st_period), int(st_multiplier), int(ema_period)
    if st_period <= 0 or st_multiplier <= 0 or ema_period <= 0 or pos_limit <= 0:
        logger.debug(f"st_period: {st_period}, st_multiplier: {st_multiplier}, ema_period: {ema_period}, "
                     f"pos_limit: {pos_limit} all must be greater than 0")
        return
    start_date, end_date = parse(start_date), parse(end_date)
    days = (end_date - start_date).days
    end_date = end_date.strftime("%Y%m%d-%H:%M:%S")
    client = IBapi()
    socket_port = 7497 if account_mode.lower() == 'paper' else 7496
    client.connect('127.0.0.1', socket_port, 123)
    client_thread = threading.Thread(target=client.run, daemon=True)
    client_thread.start()
    time.sleep(3)

    client.nextorderId += 1
    duration = f'{days} D'
    client.time_frame = time_frame

    bt_instances = list()

    for i, s in enumerate(symbols, start=client.nextorderId):
        contract = client.make_contract(s, 'STK', 'SMART', 'ISLAND')
        client.reqHistoricalData(i, contract, end_date, duration, time_frame, what_type,
                                 int(only_regular_session_data), 1, False, [])

        bt_instances.append(BackTest(client=client, unique_id=i, symbol=s, stop_loss=stop_loss,
                                     trailing_stop_loss=trailing_stop_loss, pos_limit=pos_limit,
                                     st_period=st_period, st_multiplier=st_multiplier,
                                     ema_period=ema_period, price_diff=price_diff))
        client.nextorderId += 1

    controller = Controller(bt_instances=bt_instances, output_file=output_file, charge=charges)
    controller.run()

    os.kill(os.getpid(), signal.SIGTERM)
