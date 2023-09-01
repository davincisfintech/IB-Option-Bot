import pandas as pd

from trading_bot.database.db import engine
from trading_bot.settings import BASE_DIR, logger


def calc_gross(entry_val, exit_val, side):
    return exit_val - entry_val if side.upper() == 'BUY' else entry_val - exit_val


def generate_scanned_data():
    df = pd.read_sql('scanners_source_data', engine)
    df['scan_time'] = df['scan_time'].astype(str)
    df.to_excel(BASE_DIR / 'scan_results.xlsx', index=False)
    logger.info('results generated, check scan_results.xlsx file for it')


def generate_metrics():
    df = pd.read_sql('scanner_trades_data', engine)
    # df = df[df['position_status'] == "CLOSED"]
    if not len(df):
        logger.debug('No positions yet')
        exit()
    df['entry_value'] = df['entry_price'] * df['quantity']
    df['exit_value'] = df['exit_price'] * df['quantity']
    df['gross_profit'] = df[['entry_value', 'exit_value', 'side']].apply(lambda x: calc_gross(*x), axis=1)
    del df['instruction']

    df = df.round(2)
    df = df.sort_values(by='entry_time', ascending=True)
    df.index = df['entry_time']
    df.index.names = ['index']
    df['entry_time'] = df['entry_time'].astype(str)
    df['exit_time'] = df['exit_time'].astype(str)
    total_gross = df["gross_profit"].sum()
    df.loc["total_net"] = pd.Series([total_gross], index=['gross_profit'])
    df.to_excel(BASE_DIR / 'trade_results.xlsx', index=False)
    logger.info('results generated, check trade_results.xlsx file for it')


if __name__ == '__main__':
    data = input('Press T to generate trade report and S to generate scan report: ')
    if data.strip().lower() == 't':
        generate_metrics()
    else:
        generate_scanned_data()
