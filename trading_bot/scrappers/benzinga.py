import json
import time
from queue import Queue
from threading import Thread

import websocket

from trading_bot.settings import logger, BASE_DIR


class BenzingaScraper:
    def __init__(self):
        self.ws_url = 'wss://api.benzinga.com/api/v3/news/advanced/ws'
        self.ws_client = None
        try:
            with open(BASE_DIR / 'trading_bot/scrappers/benzinga_ws_msg.json') as json_message:
                self.message_to_send = json.load(json_message)
        except FileNotFoundError as e:
            logger.exception(e)
            exit()
        self.data_queue = Queue()

    def subscribe(self):
        self.ws_client.send(json.dumps(self.message_to_send))

    def on_open(self, ws):
        pass

    def on_error(self, ws, error):
        logger.exception(f'WS Error: {error}')

    def on_close(self, ws, code, reason):
        logger.exception(f'WS Connection Expired, code: {code}, Restarting again')
        self.start_streaming()

    def on_message(self, ws, data):
        data = json.loads(data)
        if data.get('type') == 'news_sub_results':
            # logger.info(f'Raw data: {data}')
            try:
                data = data['data']['content']
            except (KeyError, TypeError) as e:
                logger.debug(e)
            for d in data:
                try:
                    quotes = d['Quotes']
                    tickers = d['Tickers']
                    title = d['Title']
                    self.data_queue.put([{'symbol': i['symbol'], 'news': title} for i in quotes])
                except (KeyError, TypeError) as e:
                    # logger.exception(e)
                    continue
                logger.info(f'Quotes: {quotes}\nTickers: {tickers}\nTitle: {title}\n')

    def start_streaming(self):
        websocket.enableTrace(False)
        self.ws_client = websocket.WebSocketApp(self.ws_url,
                                                on_message=self.on_message,
                                                on_error=self.on_error,
                                                on_close=self.on_close)
        self.ws_client.on_open = self.on_open
        self.ws_client.on_message = self.on_message
        self.ws_client.on_close = self.on_close

        # Create new thread and run it in background
        wst = Thread(target=self.ws_client.run_forever)
        wst.daemon = True
        wst.start()

        time.sleep(3)
        self.subscribe()
