import pandas as pd


def relative_strength_index(df, rsi_period, base="close"):
    delta = df[base].diff()
    up, down = delta.copy(), delta.copy()

    up[up < 0] = 0
    down[down > 0] = 0

    r_up = up.ewm(com=rsi_period - 1, adjust=False).mean()
    r_down = down.ewm(com=rsi_period - 1, adjust=False).mean().abs()

    df['rsi'] = 100 - 100 / (1 + r_up / r_down)
    df['rsi'].fillna(0, inplace=True)


def calc_gross(entry_val, exit_val, instruction):
    return exit_val - entry_val if instruction == 'BUY' else entry_val - exit_val


def charges(entry_val, exit_val):
    return 0  # -(entry_val + exit_val) * 0.01 / 100


def calc_columns(df):
    # df = df.sort_values(by='entry_time', ascending=True)
    df['entry_value'] = df['entry_price'] * df['qty']
    df['exit_value'] = df['exit_price'] * df['qty']
    df['gross_profit'] = df[['entry_value', 'exit_value', 'instruction']].apply(lambda x: calc_gross(*x), axis=1)
    df['charges'] = df[['entry_value', 'exit_value']].apply(lambda x: charges(*x), axis=1)
    df['net_profit'] = df['gross_profit'] - df['charges']
    df['pos_duration'] = df['exit_time'] - df['entry_time']
    df = df.round(2)
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
