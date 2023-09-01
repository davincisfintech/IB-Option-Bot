import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pandas as pd
import dateutil
from dateutil.parser import parse

from back_test.clients.td_client import TdaClient
from back_test.back_test import MomentumBackTest
from back_test.utils import calc_columns
from back_test.settings import logger, TZ, RECORDS_DIR, CONFIG_DIR


class Controller:
    def __init__(self, bt_instances, output_file):
        self.bt_instances = bt_instances
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
        if not os.path.exists(RECORDS_DIR):
            os.mkdir(RECORDS_DIR)
        df = pd.concat(res, axis=0)
        if not len(df):
            logger.debug('No Results Found')
            return
        logger.debug('Backtest done, exporting results to excel...')
        file = RECORDS_DIR / f'{self.output_file}_{datetime.now(tz=TZ)}.xlsx'.replace(' ', '_').replace(':', '_')
        df, records = calc_columns(df)
        records.to_excel(file, sheet_name='Results', index=False)
        logger.debug(f'Done, check {file} for results')


def run(symbols, start_date, end_date, output_file, **kwargs):
    symbols = [s.strip().upper() for s in symbols]

    try:
        days = (parse(end_date) - parse(start_date)).days
    except dateutil.parser._parser.ParserError as e:
        logger.exception(e)
        logger.debug('Please enter dates in right format')
        return
    if days <= 0:
        logger.debug('End date must be greater than start date')
        return

    # Initialize TD client
    td_client = TdaClient(token_path=CONFIG_DIR / 'td_tokens.json',
                          creds_path=CONFIG_DIR / 'config.json')
    logger.info('TD client Initialized, Authenticating...')
    td_client.login()
    benchmark_df = td_client.get_past_data(symbol='$SPX.X', start_time=start_date, end_time=end_date,
                                           extended_hours=kwargs['extended_hours_data'])
    if benchmark_df is None or not len(benchmark_df):
        logger.debug('Error getting benchmark data, please check inputs')
        return
    bt_instances = [MomentumBackTest(symbol=s, client=td_client, start_date=start_date, end_date=end_date,
                                     benchmark_df=benchmark_df, **kwargs) for s in symbols]

    controller = Controller(bt_instances=bt_instances, output_file=output_file)
    controller.run()
