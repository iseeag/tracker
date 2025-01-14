import os
from datetime import datetime
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
    login_token = Column(String, unique=True)


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


class StrategyBalanceRecord(StrategyBalance):
    account_name: str
    timestamp: datetime


class AccountBalances(BaseModel):
    name: str
    start_date: str
    preset_balances: list[StrategyBalance]
    realtime_balances: list[StrategyBalance]
    strategy_balance_records: list[StrategyBalance]
    record_start_date: str
    record_end_date: str

    @property
    def preset_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=[(balance.name, balance.balance) for balance in self.preset_balances],
            columns=['Strategy Name', 'Preset Balance']
        )

    @property
    def realtime_df(self) -> pd.DataFrame:
        preset_df = self.preset_df
        realtime_df = pd.DataFrame(
            data=[(balance.name, balance.balance) for balance in self.realtime_balances],
            columns=["Strategy Name", "Realtime Balance"]
        )
        realtime_df['Difference'] = (realtime_df['Realtime Balance'] - preset_df['Preset Balance']).round(4)
        realtime_df['Percentage Difference'] = (realtime_df['Difference'] / preset_df['Preset Balance']).round(4) * 100
        return realtime_df

    @property
    def record_df(self) -> pd.DataFrame:
        return pd.DataFrame()

    @classmethod
    def sum_preset_df(cls, balances: List['AccountBalances']) -> pd.DataFrame:
        summary = {}
        for balance in balances:
            summary[balance.name] = round(sum([b.balance for b in balance.preset_balances]), 4)
        return pd.DataFrame(summary.items(), columns=['Account Name', 'Total Preset Balance'])

    @classmethod
    def sum_realtime_df(cls, balances: List['AccountBalances']) -> pd.DataFrame:
        summary = {}
        for balance in balances:
            summary[balance.name] = round(sum([b.balance for b in balance.realtime_balances]), 4)
        sum_preset_df = cls.sum_preset_df(balances)
        sum_realtime_df = pd.DataFrame(summary.items(), columns=['Account Name', 'Total Realtime Balance'])
        sum_realtime_df['Total Difference'] = (sum_realtime_df['Total Realtime Balance'] - sum_preset_df[
            'Total Preset Balance']).round(4)
        sum_realtime_df['Percentage Difference'] = (sum_realtime_df['Total Difference'] / sum_preset_df[
            'Total Preset Balance']).round(4) * 100
        return sum_realtime_df

# Create tables
# Base.metadata.create_all(bind=engine)
