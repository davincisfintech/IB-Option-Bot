import json
from datetime import timedelta, datetime

import pandas as pd
from dateutil.parser import parse
from td.client import TDClient

from back_test.settings import logger, TZ


class TdaClient:
    def __init__(self, token_path, creds_path=None, api_key=None, redirect_url=None, account_no=None):
        if creds_path is not None:
            try:
                with open(creds_path) as config:
                    config = json.load(config)
                    api_key = config.get('td_api_key')
                    redirect_url = config.get('td_redirect_url')
                    account_no = config.get('account_no')
            except FileNotFoundError as e:
                logger.exception(e)
                raise e

        self.client = TDClient(
            client_id=api_key,
            redirect_uri=redirect_url,
            credentials_path=token_path
        )
        self.account_no = account_no

    def login(self):
        self.client.login()

    def get_past_data(self, symbol, start_time, end_time, period='', period_type='year', frequency='1',
                      frequency_type='minute', extended_hours=False):
        start_date = str(int((parse(start_time) + timedelta(days=1)).timestamp() * 1000))
        end_date = str(int((parse(end_time) + timedelta(days=1)).timestamp() * 1000))
        args = locals()
        del args['self'], args['start_time'], args['end_time']
        if frequency_type == 'minute':
            del args['period'], args['period_type']
        try:
            df = self.client.get_price_history(**args)
            df = pd.DataFrame(df['candles'])
            df['datetime'] = df['datetime'].apply(lambda x: datetime.fromtimestamp(x / 1000).astimezone(TZ))
            # df['date'] = df['datetime'].dt.date
            df = df.set_index('datetime')
            return df
        except Exception as e:
            logger.exception(e)
