import pandas as pd


def calc_gross(entry_val, exit_val, instruction):
    return exit_val - entry_val if instruction == 'BUY' else entry_val - exit_val


def charges(entry_val, exit_val, charge):
    return (entry_val + exit_val) * charge / 100


def calc_columns(df, charge):
    df = df.sort_values(by=['symbol', 'entry_time'], ascending=[True, True])
    df['entry_value'] = df['entry_price'] * df['qty']
    df['exit_value'] = df['exit_price'] * df['qty']
    df['gross_profit'] = df[['entry_value', 'exit_value', 'side']].apply(lambda x: calc_gross(*x), axis=1)
    df['charges'] = df[['entry_value', 'exit_value']].apply(lambda x: charges(*x, charge), axis=1)
    df['net_profit'] = df['gross_profit'] - df['charges']
    df['pos_duration'] = df['exit_time'] - df['entry_time']
    df = df.round(3)
    df.index = df['entry_time']
    df.index.names = ['index']
    df['entry_time'] = df['entry_time'].astype(str)
    df['exit_time'] = df['exit_time'].astype(str)
    df['pos_duration'] = df['pos_duration'].astype(str)
    records = df.copy()
    total_gross = records["gross_profit"].sum()
    total_charge = records["charges"].sum()
    total_net = records["net_profit"].sum()
    records.loc["total_net"] = pd.Series([total_gross, total_charge, total_net],
                                         index=['gross_profit', 'charges', 'net_profit'])
    return df, records


def calc_metrics(df):
    symbols = df['symbol'].unique()
    metrics = pd.DataFrame(columns=['Number_of_trades', 'total_gross_profit', 'total_charges', 'total_net_profit',
                                    'winning_trades', 'losing_trades', 'win_loss_ratio'])
    metrics.index.name = 'Name'
    for s in symbols:
        s_df = df[df['symbol'] == s]
        num_trades = len(s_df)
        total_gross = s_df['gross_profit'].sum()
        total_charges = s_df['charges'].sum()
        total_net = s_df['net_profit'].sum()
        winning_trades = len(s_df[s_df['net_profit'] > 0])
        losing_trades = len(s_df[s_df['net_profit'] < 0])
        try:
            win_loss_ratio = winning_trades / losing_trades
        except ZeroDivisionError:
            win_loss_ratio = 'inf'

        metrics.loc[s] = {'Number_of_trades': num_trades, 'total_gross_profit': total_gross,
                          'total_charges':  total_charges, 'total_net_profit': total_net,
                          'winning_trades': winning_trades, 'losing_trades': losing_trades,
                          'win_loss_ratio': win_loss_ratio}

    metrics.loc['Average'] = metrics.mean()
    metrics = metrics.round(3)
    return metrics
