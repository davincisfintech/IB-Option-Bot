#  Parameters  #

# List of symbols i.e. [symbol1, symbol2, symbol3..]
symbols = ['GS', 'SQ', 'PYPL', 'AMC', 'MMM', 'BABA', 'NFLX', 'V', 'F', 'NET']

start_date = '2022-07-01'  # date in yy-mm-dd format, start date for getting data
end_date = '2022-08-16'  # date in yy-mm-dd format, end date for getting data

pos_limit = 1000  # Position limit. i.e. 100 means $100 limit per position etc
stop_loss = 2  # Stop loss percent, for ex. 5 means 5 % etc
target = 2  # Target percent, for ex. 5 means 5 % etc

rsi_period = 14  # Period for calculating RSI

# Minimum Gap percent, gap percent should be more than this on positive side for long signal
# and less than this for short signal.
# i.e. if gap percent specified 5 then for long signal gap up should be more than 5 percent
# and for short signal gap down should be less than -5 percent
gap_percent = 1

price_limit = 2000  # Price condition. i.e. only select stocks priced less than this
rsi_lower_threshold = 30  # RSI lower threshold. i.e. RSI should be less than this for short signal
rsi_higher_threshold = 70  # RSI threshold. i.e. RSI should be greater than this for long signal
volume_period = 5  # Volume period. i.e. Number of days to consider for average volume calculation
volume_multiplier = 1.5  # Volume multiplier. i.e. Volume must be greater than avg_volume * volume_multiplier

extended_hours_data = False  # Choices True, False, if True then pre+after market data will be considered else Not

# Name of output_file, results file with this_name_{time_of_day}.xlsx will be created inside records folder
output_file = 'test'

#  Parameters End  #

if __name__ == '__main__':
    kwargs = {i: j for i, j in locals().items() if not i.startswith('__')}
    from back_test.controller import run

    run(**kwargs)