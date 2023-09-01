if __name__ == '__main__':

    from trading_bot.scrappers.benzinga import BenzingaScraper

    bz = BenzingaScraper()
    bz.start_streaming()
    while True:
        pass