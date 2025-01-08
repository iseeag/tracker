import hashlib
import os
import uuid
from datetime import date, datetime
from typing import Dict, List

import ccxt
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.orm import Session

from gr_db import (Account, AccountBalanceHistory, SessionLocal, Strategy,
                   User, UserAccountAssociation)

load_dotenv()
current_session_tokens = {}


# Function to hash tokens
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# Admin login function
def admin_login(master_token: str) -> str:
    stored_hash = os.getenv('MASTER_TOKEN')
    if hash_token(master_token) == stored_hash:
        # Generate a unique session token
        session_token = str(uuid.uuid4())
        # Save authentication token to session state
        current_session_tokens['admin'] = session_token
        logger.info("Admin login successful")
        return session_token
    logger.warning("Admin login failed: invalid master token")
    return ""


def user_login(login_token: str, db: Session) -> str:
    user = db.query(User).filter(User.login_token == login_token).first()
    if user:
        # Generate a unique session token
        session_token = str(uuid.uuid4())
        # Save authentication token to session state
        current_session_tokens[user.id] = session_token
        logger.info(f"User login successful for user: {user.name}")
        return session_token
    logger.warning("User login failed: invalid login token")
    return ""


# # Logout function
def logout(token: str):
    if token in current_session_tokens.values():
        # Remove authentication token from session state
        current_session_tokens.pop(token)
        logger.info("Logout successful")
        return True
    logger.warning("Logout failed: invalid session token")
    return False


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# User-Type Methods
def get_user_id(session_token: str):
    for user_id, token in current_session_tokens.items():
        if token == session_token:
            return user_id
    raise Exception("Invalid session token")


def retrieve_multi_info(user_id: str, db: Session):
    linked_accounts = db.query(UserAccountAssociation).filter(UserAccountAssociation.user_id == user_id).all()
    account_ids = [link.account_id for link in linked_accounts]
    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    strategies = db.query(Strategy).filter(Strategy.account_id.in_(account_ids)).all()
    return accounts, strategies


def get_preset_balance_tables(token: str, db: Session) -> Dict[str, Dict]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    preset_balances = {str(a.account_name): {'start_date': a.start_date,
                                             'strategies': [
                                                 {
                                                     'strategy_name': strategy.strategy_name,
                                                     'preset_balance': strategy.preset_balance
                                                 } for strategy in strategies if strategy.account_id == a.id]}
                       for a in accounts}
    return preset_balances


def get_realtime_balance_tables(token: str, db: Session) -> Dict[str, List]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    realtime_balances = {}
    for account in accounts:
        strategies_bal = []
        for strategy in [s for s in strategies if s.account_id == account.id]:
            exchange_class = getattr(ccxt, strategy.exchange_type.lower())
            exchange = exchange_class({
                'apiKey': strategy.api_key,
                'secret': strategy.secret_key,
                'password': strategy.passphrase
            })
            balance = exchange.fetch_balance()
            strategies_bal.append({'strategy_name': strategy.strategy_name,
                                   'realtime_balance': balance['total']})
        realtime_balances[str(account.account_name)] = strategies_bal
    return realtime_balances


def get_account_balance_history_tables(
        token: str, db: Session, page_number: int = 1, page_size: int = 10
) -> Dict[str, List]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    account_ids = [account.id for account in accounts]
    strategies_names = {s.id: s.strategy_name for s in strategies}
    balance_history = db.query(AccountBalanceHistory).filter(
        AccountBalanceHistory.account_id.in_(account_ids)).offset((page_number - 1) * page_size).limit(
        page_size).all()
    account_bal_hist = {}
    for account in accounts:
        records = [{
            'strategy_name': strategies_names[record.strategy_id],
            'balance': record.balance,
            'timestamp': record.timestamp
        } for record in balance_history if record.account_id == account.id]
        account_bal_hist[str(account.account_name)] = records
    return account_bal_hist


# Admin-Type Methods
# Account and Strategy Management

def create_account(account_name: str, start_date: str, db: Session):
    new_account = Account(account_name=account_name,
                          start_date=datetime.strptime(start_date, "%m/%d/%Y").date())
    db.add(new_account)
    db.commit()
    return new_account


def delete_account(account_name: str, db: Session):
    account = db.query(Account).filter(Account.account_name == account_name).first()
    if account:
        db.delete(account)
        db.commit()
        return True
    return False


def update_account(account_name: str, start_date: str, db: Session):
    account = db.query(Account).filter(Account.id == account_name).first()
    if account:
        account.start_date = start_date
        db.commit()
        return account
    return None


def create_strategy(account_id: str, strategy_name: str, api_key: str, secret_key: str, passphrase: str,
                    exchange_type: str, preset_balance: float, db: Session):
    new_strategy = Strategy(account_id=account_id, strategy_name=strategy_name, api_key=api_key,
                            secret_key=secret_key, passphrase=passphrase, exchange_type=exchange_type,
                            preset_balance=preset_balance)
    db.add(new_strategy)
    db.commit()
    return new_strategy


def delete_strategy(strategy_id: str, db: Session):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        db.delete(strategy)
        db.commit()
        return True
    return False


def update_strategy(strategy_id: str, api_key: str, secret_key: str, passphrase: str, exchange_type: str,
                    preset_balance: float, db: Session):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        strategy.api_key = api_key
        strategy.secret_key = secret_key
        strategy.passphrase = passphrase
        strategy.exchange_type = exchange_type
        strategy.preset_balance = preset_balance
        db.commit()
        return strategy
    return None


# User Management

def create_user(name: str, login_token: str, db: Session):
    new_user = User(name=name, login_token=login_token)
    db.add(new_user)
    db.commit()
    return new_user


def delete_user(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False


def update_user(user_id: str, login_token: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.login_token = login_token
        db.commit()
        return user
    return None


def set_linked_account_to_user(user_name: str, account_ids: List[str], db: Session):
    user_id = db.query(User).filter(User.name == user_name).first().id
    user_account_links = db.query(UserAccountAssociation).filter(
        UserAccountAssociation.user_id == user_id,
        UserAccountAssociation.account_id.in_(account_ids)).all()
    linked_account_ids = [link.account_id for link in user_account_links]
    for account_id in [account for account in account_ids if account not in linked_account_ids]:
        new_link = UserAccountAssociation(user_id=user_id, account_id=account_id)
        db.add(new_link)
        logger.info(f"Linked account {account_id} to user {user_name}")
    for link in user_account_links:
        if link.account_id not in account_ids:
            db.delete(link)
            logger.info(f"Unlinked account {link.account_id} from user {user_name}")
    db.commit()
    return False


# Backend Utility Methods

def get_linked_accounts(user_id: str, db: Session):
    linked_accounts = db.query(UserAccountAssociation).filter(UserAccountAssociation.user_id == user_id).all()
    account_ids = [link.account_id for link in linked_accounts]
    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    return accounts


def get_account_information(account_ids: list, db: Session):
    accounts_info = db.query(Account).filter(Account.id.in_(account_ids)).all()
    return [{
        'account_id': account.id,
        'account_name': account.account_name,
        'start_date': account.start_date
    } for account in accounts_info]


def sum_balance_tables(balances: list):
    total_preset_balance = sum(balance['preset_balance'] for balance in balances if 'preset_balance' in balance)
    total_realtime_balance = sum(balance['realtime_balance'] for balance in balances if 'realtime_balance' in balance)
    total_difference = total_realtime_balance - total_preset_balance
    total_percentage_difference = (total_difference / total_preset_balance) * 100 if total_preset_balance else 0
    return {
        'total_preset_balance': total_preset_balance,
        'total_realtime_balance': total_realtime_balance,
        'total_difference': total_difference,
        'total_percentage_difference': total_percentage_difference
    }


# Scheduled Tasks with APScheduler

def daily_balance_snapshot(db: Session):
    accounts = db.query(Account).all()
    for account in accounts:
        strategies = db.query(Strategy).filter(Strategy.account_id == account.id).all()
        for strategy in strategies:
            exchange_class = getattr(ccxt, strategy.exchange_type.lower())
            exchange = exchange_class({
                'apiKey': strategy.api_key,
                'secret': strategy.secret_key,
                'password': strategy.passphrase
            })
            balance = exchange.fetch_balance()
            total_balance = balance['total']
            for currency, amount in total_balance.items():
                new_record = AccountBalanceHistory(
                    account_id=account.id,
                    strategy_name=strategy.strategy_name,
                    balance=amount,
                    timestamp=datetime.now()
                )
                db.add(new_record)
    db.commit()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: daily_balance_snapshot(next(get_db())), 'cron', hour=0, minute=0)
    scheduler.start()

# Uncomment the line below to start the scheduler when running this module
# start_scheduler()
