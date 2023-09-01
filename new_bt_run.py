#  Parameters  #

account_mode = 'Paper'  # Choices Live, Paper. Live if Live account is open and Paper if paper account is open in IB TWS

# Symbols to backtest. format ['symbol_1', 'symbol_2', ...]
symbols = ['TSLA', 'AAPL', 'GOOGL']

start_date = '2022-11-01'  # date in yy-mm-dd format, start date for backtest
end_date = '2022-12-31'  # date in yy-mm-dd format, end date for backtest

# Time frame of candles
# i.e. 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins, 20 mins, 30 mins, 1 hour, 2 hours, 3 hours, 4 hours, 1 day
time_frame = '15 mins'

stop_loss = 100  # Stop loss percentage
trailing_stop_loss = False  # Trailing Stop loss. Choice True, False. True to trail and False to not trail.

# Position limit in $.
# for ex. if this value is 1000 then only take trade worth 1000, i.e. if price is 100 then only buy 10 quantity
pos_limit = 1000

st_period = 10   # Period for Super trend calculation
st_multiplier = 2  # Multiplier for Super trend calculation
ema_period = 14  # Period for EMA calculation
price_diff = 1  # Price diff percent to calculate difference between super trend line and candle high/low

charges = 0.02  # Enter percentage to consider as commission + charges

# Choice: True, False. True to get only get regular session data and False to get pre-market and after-market data
only_regular_session_data = True

what_type = 'TRADES'  # Type of data required, i.e. TRADES, BID_ASK, BID, ASK, MIDPOINT etc

# Name of the output file which will contain results.
# this file will be created inside records folder with name {output_file}_{time_of_the_day}.xlsx
output_file = 'test'

#  Parameters End  #

if __name__ == '__main__':
    kwargs = {i: j for i, j in locals().items() if not i.startswith('__')}
    from new_back_test.controller import run

    run(**kwargs)
