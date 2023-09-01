# Parameters

trading_mode = 'Paper'  # Choices Live, Paper, Live for Live trading and Paper for paper trading

# Position Limit as percentage of total account balance,
# i.e. 1 means 1 % of account balance to use for trading for each position
pos_limit = 1

# Limit for open orders/positions. i.e. at a time only have specified open orders/positions
stock_limit = 5

stop_loss = 1  # Stop loss percent, for ex. 5 means 5 % etc
target = 1  # Target percent, for ex. 5 means 5 % etc

order_type = 'MKT'  # Choices, LMT or MKT, LMT for limit order and MKT for market order

#  Choices True, False. if True then run only using market-depth conditions and ignore filter
# if False then first do filter check before market depth check
run_without_filter = False

# Screening parameters
rsi_period = 14  # Period for calculating RSI

# Minimum Gap percent, gap percent should be more than this on positive side for long signal
# and less than this for short signal.
# i.e. if gap percent specified 5 then for long signal gap up should be more than 5 percent
# and for short signal gap down should be less than -5 percent
gap_percent = -5

price_limit = 2000  # Price condition. i.e. only select stocks priced less than this
rsi_lower_threshold = 49  # RSI lower threshold. i.e. RSI should be less than this for short signal
rsi_higher_threshold = 51  # RSI threshold. i.e. RSI should be greater than this for long signal
volume_period = 5  # Volume period. i.e. Number of days to consider for average volume calculation
volume_multiplier = 0.5  # Volume multiplier. i.e. Volume must be greater than avg_volume * volume_multiplier

# Choices True, False. If True then delete open orders and positions from db else not
# Caution: only set it to true if you want to delete all open orders and positions from db and start fresh positions
clear_open_orders_and_positions_from_db = False


# Parameters End

if __name__ == '__main__':
    kwargs = {i: j for i, j in locals().items() if not i.startswith('__')}
    from trading_bot.controllers.controller_2 import main

    main(**kwargs)
