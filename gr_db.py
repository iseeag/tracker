from sqlalchemy import create_engine, Column, String, Date, Float, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Accounts Table
class Account(Base):
    __tablename__ = 'accounts'

    account_name = Column(String, primary_key=True, index=True)
    start_date = Column(Date)

    strategies = relationship('Strategy', back_populates='account')
    users = relationship('User', secondary='user_accounts', back_populates='accounts')

# Strategies Table
class Strategy(Base):
    __tablename__ = 'strategies'

    id = Column(String, primary_key=True, index=True)
    account_name = Column(String, ForeignKey('accounts.account_name'))
    strategy_name = Column(String)
    api_key = Column(String)
    secret_key = Column(String)
    passphrase = Column(String, nullable=True)
    exchange_type = Column(String)
    preset_balance = Column(Float)

    account = relationship('Account', back_populates='strategies')

# Users Table
class User(Base):
    __tablename__ = 'users'

    name = Column(String, primary_key=True, index=True)
    login_token = Column(String)

    accounts = relationship('Account', secondary='user_accounts', back_populates='users')

# User_Accounts Association Table
user_accounts = Table(
    'user_accounts', Base.metadata,
    Column('user_name', String, ForeignKey('users.name')),
    Column('account_name', String, ForeignKey('accounts.account_name'))
)

# Account_Balance_History Table
class AccountBalanceHistory(Base):
    __tablename__ = 'account_balance_history'

    id = Column(String, primary_key=True, index=True)
    account_name = Column(String, ForeignKey('accounts.account_name'))
    strategy_name = Column(String)
    balance = Column(Float)
    timestamp = Column(Date)

# Create tables
Base.metadata.create_all(bind=engine)
