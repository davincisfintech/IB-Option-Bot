import logging
import os
from datetime import datetime
from pathlib import Path

import pytz
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
TZ = pytz.timezone('US/Eastern')
config = dotenv_values(BASE_DIR / '.env')

USER = config['USER']
PASSWORD = config['PASSWORD']
HOSTNAME = config['HOSTNAME']
PORT = config['PORT']
DB_NAME = config['DB_NAME']
bba_url = 'https://sa3.blackboxstocks.com/signalr/connect?transport=serverSentEvents&clientProtocol=2.1&' \
          'connectionToken=eKkvh2FQ5TRck4hbU1KGebGmCU5zw0WIjNsMrMGGRe8ba7eECLlylBi4sbG9NS9Faib%2B3%2B4PQALdPcHcoXqysi' \
          'JVwGyavpz9bElUwVk019GZQsNeHjMbdQQb7vCTZz1P&' \
          'connectionData=%5B%7B%22name%22%3A%22popupnotification%22%7D%5D&tid=10'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(message)s')

if not os.path.exists(BASE_DIR / "logs"):
    os.mkdir(BASE_DIR / "logs")
file_handler = logging.FileHandler(BASE_DIR / f'logs/{datetime.now(tz=TZ).date()}_trades.log')

file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def customTime(*args):
    utc_dt = pytz.utc.localize(datetime.utcnow())
    converted = utc_dt.astimezone(TZ)
    return converted.timetuple()


logging.Formatter.converter = customTime
