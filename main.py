# Parameters

# Trading parameters
trading_mode = 'Paper'  # Trading mode, choices Live or Paper
order_type = 'MKT'  # Choices, LMT or MKT, LMT for limit order and MKT for market order
position_limit = 100  # Position size in USD

# Screening parameters
rsi_period = 14  # Period for calculating RSI
gap_percent = -5  # Minimum Gap up percent
price_limit = 2000  # Price condition. i.e. only select stocks priced less than this
rsi_threshold = 50  # RSI threshold. i.e. RSI should be greater than tis
volume_period = 5  # Volume period. i.e. Number of days to consider for average volume calculation
volume_multiplier = 2  # Volume multiplier. i.e. Volume must be greater than avg_volume * volume_multiplier

# Parameters end


if __name__ == '__main__':
    kwargs = {i: j for i, j in locals().items() if not i.startswith('__')}
    from trading_bot.controllers.controller_1 import run

    run(**kwargs)
