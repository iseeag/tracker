import os
from typing import List

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import Column, Date, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
load_dotenv()

# Database connection
APP_PREFIX = 'gr_'
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Accounts Table
class Account(Base):
    __tablename__ = APP_PREFIX + 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_name = Column(String, unique=True)
    start_date = Column(Date)


# Strategies Table
class Strategy(Base):
    __tablename__ = APP_PREFIX + 'strategies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_name = Column(String)
    strategy_name = Column(String)
    api_key = Column(String)
    secret_key = Column(String)
    passphrase = Column(String, nullable=True)
    exchange_type = Column(String)
    preset_balance = Column(Float)


# Users Table
class User(Base):
    __tablename__ = APP_PREFIX + 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    login_token = Column(String)


class UserAccountAssociation(Base):
    __tablename__ = APP_PREFIX + 'user_accounts_association'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    account_id = Column(Integer)


# Account_Balance_History Table
class AccountBalanceHistory(Base):
    __tablename__ = APP_PREFIX + 'account_balance_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer)
    strategy_id = Column(Integer)
    balance = Column(Float)
    timestamp = Column(Date)


class StrategyBalance(BaseModel):
    name: str
    balance: float


class AccountBalances(BaseModel):
    name: str
    strategy_balances: list[StrategyBalance]


class PresetAccountBalance(AccountBalances):
    start_date: str

    def to_table(self) -> pd.DataFrame:
        ...

    @classmethod
    def sum_to_table(cls, balances: List['PresetAccountBalance']) -> pd.DataFrame:
        # sum_balance = [{"strategy_name": s.strategy_name,
        #                 "total_preset_balance": sum([s.preset_balance for s in strategies
        #                                              if s.strategy_name == s.strategy_name])
        #                 } for s in strategies]
        ...


class RealtimeAccountBalance(AccountBalances):
    ...

    def to_table(self, preset_balance: PresetAccountBalance) -> pd.DataFrame:
        ...

    @classmethod
    def sum_to_table(cls,
                     realtime_balances: List['RealtimeAccountBalance'],
                     preset_balances: List[PresetAccountBalance]) -> pd.DataFrame:
        # realtime_strategy_balances = []
        # sum_balance = [{"strategy_name": s['strategy_name'],
        #                 "realtime_balance": sum([s['realtime_balance'] for s in realtime_strategy_balances
        #                                          if s['strategy_name'] == s['strategy_name']])
        #                 } for s in strategies]

        ...


class StrategyBalanceRecord(StrategyBalance):
    account_name: str
    timestamp: str

    @classmethod
    def to_table(cls, preset_balance: PresetAccountBalance, records: List['StrategyBalanceRecord']) -> pd.DataFrame:
        ...


# Create tables
# Base.metadata.create_all(bind=engine)
