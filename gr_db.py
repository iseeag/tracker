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
    timestamp: datetime


class AccountBalances(BaseModel):
    name: str
    start_date: str
    preset_balances: List[StrategyBalance]
    realtime_balances: List[StrategyBalance]
    strategy_balance_records: List[StrategyBalanceRecord]
    record_start_date: str
    record_end_date: str

    @property
    def account_df(self) -> pd.DataFrame:
        account_df = pd.DataFrame(
            data=[(preset_balance.name, preset_balance.balance, realtime_balance.balance)
                  for preset_balance, realtime_balance in zip(self.preset_balances, self.realtime_balances)],
            columns=["Strategy Name", "Preset Balance $", "Realtime Balance $"]
        )
        account_df['Difference $'] = (account_df['Realtime Balance $'] - account_df['Preset Balance $']).round(4)
        account_df['Percentage Difference %'] = (account_df['Difference $'] / account_df['Preset Balance $']).round(
            4) * 100
        return account_df

    @property
    def record_df(self) -> pd.DataFrame:
        record_by_date = {}
        for record in self.strategy_balance_records:
            record_date = record.timestamp.strftime('%Y-%m-%d')
            if record_date not in record_by_date:
                record_by_date[record_date] = {}
            record_by_date[record_date] = record_by_date[record_date] | {record.name: record.balance}
        record_by_date = [(date, record) for date, record in record_by_date.items()]
        record_by_date = sorted(record_by_date, key=lambda x: x[0])
        data = []
        presets = [balance.balance for balance in self.preset_balances]
        for date, record in record_by_date:
            hists = [round(record.get(p.name, float('nan')), 4) for p in self.preset_balances]
            diffs = [round(hist - preset, 4) for hist, preset in zip(hists, presets)]
            percents = [round(diff / preset * 100, 4) if not pd.isna(diffs) else float('nan')
                        for diff, preset in zip(diffs, presets)]
            hist_sum = sum([h for h in hists if not pd.isna(h)])
            diff_sum = sum([d for d in diffs if not pd.isna(d)])
            percent_sum = round(diff_sum / sum(presets) * 100, 4)
            data.append([date, *hists, hist_sum, *diffs, diff_sum, *percents, percent_sum])
        columns = ['Date', *[f'{balance.name} $' for balance in self.preset_balances], 'Total Balance $',
                   *[f'Δ{balance.name} $' for balance in self.preset_balances], 'Total Δ $',
                   *[f'%Δ{balance.name}' for balance in self.preset_balances], 'Total %Δ']
        record_df = pd.DataFrame(data, columns=columns)
        return record_df

    @classmethod
    def sum_df(cls, balances: List['AccountBalances']) -> pd.DataFrame:
        summary = []
        for balance in balances:
            summary.append((
                balance.name,
                round(sum([b.balance for b in balance.preset_balances]), 4),
                round(sum([b.balance for b in balance.realtime_balances]), 4),
            ))
        sum_df = pd.DataFrame(summary, columns=['Account Name', 'Total Preset Balance $', 'Total Realtime Balance $'])
        sum_df['Total Difference $'] = sum_df['Total Realtime Balance $'] - sum_df['Total Preset Balance $']
        sum_df['Percentage Difference %'] = (sum_df['Total Difference $'] / sum_df['Total Preset Balance $']).round(
            4) * 100
        return sum_df


# Create tables
# Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    dummy_df = pd.DataFrame(
        data=[('Strategy 1', 100.0, datetime.now()),
              ('Strategy 2', None, None),
              ('Strategy 3', 300.0, datetime.now())],
        columns=['Strategy Name', 'Balance', 'Timestamp']
    )
