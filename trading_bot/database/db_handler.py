import warnings

from trading_bot.database.db import TradesDataAll, session, ScannerTradesData
from trading_bot.settings import logger

warnings.filterwarnings('ignore')


def save_trade(action, params):
    if action == 'make_entry':
        obj = TradesDataAll(**params)
        obj.save_to_db()
        logger.debug(f'Trade Saved for {params["symbol"]} for action: {action}')
    elif action == 'confirm_entry':
        obj = session.query(TradesDataAll).filter(TradesDataAll.trade_id == params['trade_id'],
                                                  TradesDataAll.symbol == params['symbol'],
                                                  TradesDataAll.entry_order_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Trade not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.entry_time = params['entry_time']
        obj.entry_price = params['entry_price']
        obj.stop_loss = params['stop_loss']
        obj.target = params['target']
        obj.entry_order_status = params['entry_order_status']
        obj.position_status = params['position_status']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')
    elif action == 'make_exit':
        obj = session.query(TradesDataAll).filter(TradesDataAll.trade_id == params['trade_id'],
                                                  TradesDataAll.symbol == params['symbol'],
                                                  TradesDataAll.position_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Position not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.sl_exit_order_id = params['sl_exit_order_id']
        obj.sl_exit_order_time = params['sl_exit_order_time']
        obj.sl_exit_order_price = params['sl_exit_order_price']
        obj.sl_exit_order_status = params['sl_exit_order_status']
        obj.tr_exit_order_id = params['tr_exit_order_id']
        obj.tr_exit_order_time = params['tr_exit_order_time']
        obj.tr_exit_order_price = params['tr_exit_order_price']
        obj.tr_exit_order_status = params['tr_exit_order_status']
        obj.instruction = params['instruction']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')
    elif action == 'confirm_exit':
        obj = session.query(TradesDataAll).filter(TradesDataAll.trade_id == params['trade_id'],
                                                  TradesDataAll.symbol == params['symbol'],
                                                  TradesDataAll.position_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Open Position not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.position_status = params['position_status']
        obj.exit_time = params['exit_time']
        obj.exit_price = params['exit_price']
        obj.exit_type = params['exit_type']
        obj.sl_exit_order_status = params['sl_exit_order_status']
        obj.tr_exit_order_status = params['tr_exit_order_status']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')


def save_scan_bot_trade(action, params):
    if action == 'make_entry':
        obj = ScannerTradesData(**params)
        obj.save_to_db()
        logger.debug(f'Trade Saved for {params["symbol"]} for action: {action}')
    elif action == 'confirm_entry':
        obj = session.query(ScannerTradesData).filter(ScannerTradesData.trade_id == params['trade_id'],
                                                      ScannerTradesData.symbol == params['symbol'],
                                                      ScannerTradesData.entry_order_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Trade not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.entry_time = params['entry_time']
        obj.entry_price = params['entry_price']
        obj.entry_order_status = params['entry_order_status']
        obj.position_status = params['position_status']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')
    elif action == 'make_exit':
        obj = session.query(ScannerTradesData).filter(ScannerTradesData.trade_id == params['trade_id'],
                                                      ScannerTradesData.symbol == params['symbol'],
                                                      ScannerTradesData.position_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Position not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.sl_exit_order_id = params['exit_order_id']
        obj.sl_exit_order_time = params['exit_order_time']
        obj.sl_exit_order_price = params['exit_order_price']
        obj.sl_exit_order_status = params['exit_order_status']
        obj.instruction = params['instruction']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')
    elif action == 'confirm_exit':
        obj = session.query(ScannerTradesData).filter(ScannerTradesData.trade_id == params['trade_id'],
                                                      ScannerTradesData.symbol == params['symbol'],
                                                      ScannerTradesData.position_status == 'OPEN').first()
        if not obj:
            logger.debug(f'Open Position not found for {params["symbol"]}, trade_id: {params["trade_id"]}')
            return
        obj.position_status = params['position_status']
        obj.exit_time = params['exit_time']
        obj.exit_price = params['exit_price']
        obj.exit_type = params['exit_type']
        obj.sl_exit_order_status = params['exit_order_status']
        obj.commit_changes()
        logger.debug(f'Trade modified for {params["symbol"]} for action: {action}')
