import os

from dotenv import load_dotenv
from sqlalchemy import Column, Date, Float, String, create_engine
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

    id = Column(String, primary_key=True, index=True)
    account_name = Column(String, unique=True)
    start_date = Column(Date)


# Strategies Table
class Strategy(Base):
    __tablename__ = APP_PREFIX + 'strategies'

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String)
    strategy_name = Column(String)
    api_key = Column(String)
    secret_key = Column(String)
    passphrase = Column(String, nullable=True)
    exchange_type = Column(String)
    preset_balance = Column(Float)


# Users Table
class User(Base):
    __tablename__ = APP_PREFIX + 'users'

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True)
    login_token = Column(String)


class UserAccountAssociation(Base):
    __tablename__ = APP_PREFIX + 'user_accounts_association'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    account_id = Column(String)


# Account_Balance_History Table
class AccountBalanceHistory(Base):
    __tablename__ = APP_PREFIX + 'account_balance_history'

    id = Column(String, primary_key=True, index=True)
    account_id = Column(String)
    strategy_id = Column(String)
    balance = Column(Float)
    timestamp = Column(Date)


# Create tables
Base.metadata.create_all(bind=engine)
