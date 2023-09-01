# Parameters

trading_mode = 'Paper'  # Choices Live, Paper, Live for Live trading and Paper for paper trading

enable_benzinga = True  # Choice True, False. set to True to enable benzinga source and set False to disable it

# Position Limit as percentage of total account balance,
# i.e. 1 means 1 % of account balance to use for trading for each position
pos_limit = 1

# Limit for open orders/positions. i.e. at a time only have specified open orders/positions
stock_limit = 5

order_type = 'MKT'  # Choices, LMT or MKT, LMT for limit order and MKT for market order
top_gainers_to_track = 10   # Number of top gainers to scan
top_gainers_to_trade = 5   # Number of top gainers to trade, i.e. if stock enter this number then only trade
exit_percent = 5  # Make exit if gain percentage falls by this percentage

above_price = .1   # Price must be above this
below_price = 2000   # Price must be below this
above_volume = 100000   # Volume must be above this
average_volume_period = 3  # In minute, i.e. if 3 then 3 minute average volume
average_volume = 1000000   # Average volume for specified period must be above this
short_sma_period = 20   # Period for short term sma period
long_sma_period = 50   # Period for long term sma period
market_cap_usd = 10000000  # Market cap must be above this
rsi_period = 14  # Period for rsi calculation
rsi_upper_threshold = 60   # Rsi upper threshold, i.e. only buy if rsi above this level
rsi_lower_threshold = 40   # Rsi lower threshold, i.e. only sell if rsi below this level


# Choices True, False. If True then delete open orders and positions from db else not
# Caution: only set it to true if you want to delete all open orders and positions from db and start fresh positions
clear_open_orders_and_positions_from_db = False


# Parameters End

if __name__ == '__main__':
    kwargs = {i: j for i, j in locals().items() if not i.startswith('__')}
    from trading_bot.controllers.scanner_controller import main

    main(**kwargs)
