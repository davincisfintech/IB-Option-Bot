import json
from queue import Queue
from threading import Thread

from sseclient import SSEClient

from trading_bot.settings import logger, bba_url


class BlackBoxStocksScraper:
    def __init__(self):
        self.url = bba_url
        self.sse_client = None
        self.data_queue = Queue()

    def on_message(self):
        messages = SSEClient(self.url)
        for msg in messages:
            if msg.data and msg.data != 'initialized':
                try:
                    data = json.loads(msg.data)
                    if data.get('M') and len(data['M']):
                        data = data['M'][0]['A'][0]
                        data = [{'symbol': d['Symbol'], 'type': d['Type'], 'price': d['CurrentPrice'],
                                 'message': d['Message']} for d in data]
                        self.data_queue.put(data)
                        logger.info(f'Black Box data received: {data}')
                except json.decoder.JSONDecodeError as e:
                    logger.exception(e)
                    logger.debug(msg.data)
                    continue

    def start_streaming(self):
        # Create new thread and run it in background
        wst = Thread(target=self.on_message)
        wst.daemon = True
        wst.start()

