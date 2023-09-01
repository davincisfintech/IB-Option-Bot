from sqlalchemy import Column, String, Integer, DECIMAL, Float, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from trading_bot.settings import logger, USER, PASSWORD, HOSTNAME, PORT, DB_NAME

db_connection_url = f'postgresql+psycopg2://{USER}:{PASSWORD}@{HOSTNAME}:{PORT}/{DB_NAME}'

engine = create_engine(db_connection_url, echo=False)
base = declarative_base()


class ScannerTradesData(base):
    __tablename__ = 'scanner_trades_data'
    trading_mode = Column(String)
    trade_id = Column(String, primary_key=True, unique=True)
    symbol = Column(String, primary_key=True)
    side = Column(String)
    instruction = Column(String)
    quantity = Column(Integer)
    entry_order_time = Column(DateTime)
    entry_order_price = Column(DECIMAL)
    entry_order_status = Column(String)
    initial_change = Column(DECIMAL)
    entry_order_id = Column(String, primary_key=True)
    entry_price = Column(DECIMAL, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    position_status = Column(String, nullable=True)
    exit_order_time = Column(DateTime, nullable=True)
    exit_order_price = Column(DECIMAL, nullable=True)
    exit_order_status = Column(String, nullable=True)
    exit_order_id = Column(String, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_type = Column(String, nullable=True)
    exit_price = Column(DECIMAL, nullable=True)
    scan_name = Column(String)
    rsi_period = Column(Integer)
    rsi = Column(DECIMAL)
    average_volume_period = Column(Integer)
    avg_volume = Column(DECIMAL)
    volume = Column(Integer)
    rank = Column(Integer)
    long_sma_period = Column(Integer)
    long_sma = Column(DECIMAL)
    short_sma_period = Column(Integer)
    short_sma = Column(DECIMAL)

    def __repr__(self):
        return f"<symbol: {self.symbol}, scan: {self.scan_name} side: {self.side}, status: {self.status}>"

    def save_to_db(self):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()

    def delete_from_db(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def commit_changes():
        try:
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()


class TradesDataAll(base):
    __tablename__ = 'trades_data_all'
    trading_mode = Column(String)
    trade_id = Column(String, primary_key=True, unique=True)
    symbol = Column(String, primary_key=True)
    side = Column(String)
    instruction = Column(String)
    quantity = Column(Integer)
    entry_order_time = Column(DateTime)
    entry_order_price = Column(DECIMAL)
    entry_order_status = Column(String)
    entry_order_id = Column(String, primary_key=True)
    entry_price = Column(DECIMAL, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    stop_loss = Column(DECIMAL, nullable=True)
    target = Column(DECIMAL, nullable=True)
    position_status = Column(String, nullable=True)
    sl_exit_order_time = Column(DateTime, nullable=True)
    sl_exit_order_stop_price = Column(DECIMAL, nullable=True)
    sl_exit_order_price = Column(DECIMAL, nullable=True)
    sl_exit_order_status = Column(String, nullable=True)
    sl_exit_order_id = Column(String, nullable=True)
    tr_exit_order_time = Column(DateTime, nullable=True)
    tr_exit_order_price = Column(DECIMAL, nullable=True)
    tr_exit_order_status = Column(String, nullable=True)
    tr_exit_order_id = Column(String, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    exit_type = Column(String, nullable=True)
    exit_price = Column(DECIMAL, nullable=True)

    def __repr__(self):
        return f"<symbol: {self.symbol}, side: {self.side}, qty: {self.quantity}, status: {self.status}>"

    def save_to_db(self):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()

    def delete_from_db(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def commit_changes():
        try:
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()


class TradesData(base):
    __tablename__ = 'trades_data'
    trading_mode = Column(String)
    trade_id = Column(String, primary_key=True, unique=True)
    symbol = Column(String, primary_key=True)
    instruction = Column(String)
    quantity = Column(Integer)
    order_time = Column(DateTime)
    order_price = Column(DECIMAL)
    order_status = Column(String)
    order_id = Column(String, primary_key=True)
    entry_price = Column(DECIMAL, nullable=True)
    entry_time = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<symbol: {self.symbol}, instruction: {self.instruction}, quantity: {self.quantity}>"

    def save_to_db(self):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()

    def delete_from_db(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def commit_changes():
        try:
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()


class ScannedData(base):
    __tablename__ = 'scanned_data'
    symbol = Column(String, primary_key=True)
    scan_time = Column(DateTime, primary_key=True)
    price = Column(Float)
    rsi = Column(Float)
    volume = Column(Integer)
    gap_percent = Column(Float)
    news_title = Column(String)

    def __repr__(self):
        return f"<symbol: {self.symbol}, instruction: {self.scan_time}>"

    def save_to_db(self):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()

    def delete_from_db(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def commit_changes():
        try:
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()


class ScannersSourceData(base):
    __tablename__ = 'scanners_source_data'
    symbol = Column(String, primary_key=True)
    scan_time = Column(DateTime, primary_key=True)
    source_1 = Column(String)
    source_2 = Column(String)
    scan_type = Column(String)
    rank = Column(Integer)

    def __repr__(self):
        return f"<symbol: {self.symbol}, scan time: {self.scan_time}>"

    def save_to_db(self):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()

    def delete_from_db(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def commit_changes():
        try:
            session.commit()
        except Exception as e:
            logger.exception(e)
            session.rollback()
        finally:
            session.close()


Session = sessionmaker(engine)
Session = scoped_session(Session)
session = Session()

base.metadata.create_all(engine)
