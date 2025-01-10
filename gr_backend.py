import hashlib
import os
import uuid
from datetime import datetime
from typing import Dict, List

import ccxt
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.orm import Session

from gr_db import (Account, AccountBalanceHistory, AccountBalances,
                   PresetAccountBalance, RealtimeAccountBalance, SessionLocal,
                   Strategy, StrategyBalance, StrategyBalanceRecord, User,
                   UserAccountAssociation)

load_dotenv()
current_session_tokens = {}


# Function to hash tokens
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# Admin login function
def admin_login(master_token: str) -> str:
    stored_master_token = os.getenv('MASTER_TOKEN')
    if master_token == stored_master_token:
        # Generate a unique session token
        session_token = str(uuid.uuid4())
        # Save authentication token to session state
        current_session_tokens['admin'] = session_token
        logger.info(f"Admin login successful! {current_session_tokens}")
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
        logger.info(f"User login successful for user: {user.name}, {current_session_tokens}")
        return session_token
    logger.warning("User login failed: invalid login token")
    return ""


# # Logout function
def logout(token: str):
    if token in current_session_tokens.values():
        # Remove authentication token from session state
        key = [k for k, v in current_session_tokens.items() if v == token][0]
        current_session_tokens.pop(key)
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


def get_preset_balances(token: str, db: Session) -> Dict[str, PresetAccountBalance]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    # preset_balances = {str(a.account_name): {'start_date': a.start_date,
    #                                          'strategies': [
    #                                              {
    #                                                  'strategy_name': strategy.strategy_name,
    #                                                  'preset_balance': strategy.preset_balance
    #                                              } for strategy in strategies if strategy.account_id == a.id]}
    #                    for a in accounts}
    preset_balances = {str(a.account_name): PresetAccountBalance(
        name=str(a.account_name),
        start_date=str(a.start_date),
        strategy_balances=[
            StrategyBalance(name=str(s.strategy_name),
                            balance=float(s.preset_balance))
            for s in strategies if s.account_id == a.id])
        for a in accounts}
    return preset_balances


def get_realtime_balances(token: str, db: Session) -> Dict[str, RealtimeAccountBalance]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    realtime_balances = {}
    # for account in accounts:
    #     strategies_bal = []
    #     for strategy in [s for s in strategies if s.account_id == account.id]:
    #         strategy_balance = retrieve_strategy_balance(strategy)
    #         data = {'strategy_name': strategy.strategy_name,
    #                 'realtime_balance': strategy_balance}
    #         strategies_bal.append(data)
    #         realtime_strategy_balances.append(data)
    #     realtime_balances[str(account.account_name)] = strategies_bal
    for account in accounts:
        records = [StrategyBalance(
            name=str(strategy.strategy_name),
            balance=float(retrieve_strategy_balance(strategy))
        ) for strategy in [s for s in strategies if s.account_id == account.id]]
        realtime_balance = RealtimeAccountBalance(name=str(account.account_name),
                                                  strategy_balances=records)
        realtime_balances[str(account.account_name)] = realtime_balance
    return realtime_balances


def get_account_balance_history_tables(
        token: str, db: Session, page_number: int = 1, page_size: int = 10
) -> Dict[str, List[StrategyBalanceRecord]]:
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    account_ids = [account.id for account in accounts]
    strategies_names = {s.id: s.strategy_name for s in strategies}
    balance_history = db.query(AccountBalanceHistory).filter(
        AccountBalanceHistory.account_id.in_(account_ids)).offset((page_number - 1) * page_size).limit(
        page_size).all()
    account_bal_hist = {}
    for account in accounts:
        # records = [{
        #     'strategy_name': strategies_names[record.strategy_id],
        #     'balance': record.balance,
        #     'timestamp': record.timestamp
        # } for record in balance_history if record.account_id == account.id]
        records = [StrategyBalanceRecord(
            name=str(strategies_names[record.strategy_id]),
            account_name=str(account.account_name),
            balance=float(record.balance),
            timestamp=str(record.timestamp)
        ) for record in balance_history if record.account_id == account.id]
        account_bal_hist[str(account.account_name)] = records
    return account_bal_hist


# Admin-Type Methods
# Account and Strategy Management
def check_admin_token(token: str) -> bool:
    if current_session_tokens.get('admin') != token:
        raise Exception("Unauthorized access")


def create_account(token: str, account_name: str, start_date: str, db: Session):
    check_admin_token(token)
    new_account = Account(account_name=account_name,
                          start_date=datetime.strptime(start_date, "%m/%d/%Y").date())
    db.add(new_account)
    db.commit()
    return new_account


def delete_account(token: str, account_name: str, db: Session):
    check_admin_token(token)
    account = db.query(Account).filter(Account.account_name == account_name).first()
    if account:
        db.delete(account)
        user_account_links = db.query(UserAccountAssociation).filter(
            UserAccountAssociation.account_id == account.id).all()
        for link in user_account_links:
            db.delete(link)
        strategies = db.query(Strategy).filter(Strategy.account_id == account.id).all()
        for strategy in strategies:
            db.delete(strategy)
        db.commit()
        logger.info(f"Deleted account {account_name} and its strategies and associations")
        return True
    return False


def update_account(token: str, account_name: str, start_date: str, db: Session):
    check_admin_token(token)
    account = db.query(Account).filter(Account.id == account_name).first()
    if account:
        account.start_date = start_date
        db.commit()
        return account
    return None


def list_accounts(token: str, db: Session):
    check_admin_token(token)
    accounts = db.query(Account).all()
    return accounts


def create_strategy(token: str, account_id: str, strategy_name: str, api_key: str, secret_key: str, passphrase: str,
                    exchange_type: str, preset_balance: float, db: Session):
    check_admin_token(token)
    new_strategy = Strategy(
        account_id=account_id,
        strategy_name=strategy_name,
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        exchange_type=exchange_type,
        preset_balance=preset_balance
    )
    db.add(new_strategy)
    db.commit()
    return new_strategy


def delete_strategy(token: str, strategy_id: str, db: Session):
    check_admin_token(token)
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        db.delete(strategy)
        db.commit()
        return True
    return False


def update_strategy(token: str, strategy_id: str, api_key: str, secret_key: str, passphrase: str, exchange_type: str,
                    preset_balance: float, db: Session):
    check_admin_token(token)
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

def create_user(token: str, name: str, login_token: str, db: Session):
    check_admin_token(token)
    new_user = User(name=name, login_token=login_token)
    db.add(new_user)
    db.commit()
    return new_user


def delete_user(token: str, user_id: str, db: Session):
    check_admin_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        # Delete all user-account associations
        user_account_links = db.query(UserAccountAssociation).filter(
            UserAccountAssociation.user_id == user_id).all()
        for link in user_account_links:
            db.delete(link)
        # Delete the user
        db.delete(user)
        db.commit()
        logger.info(f"Deleted user {user_id} and its associations")
        return True
    return False


def update_user(token: str, user_id: str, login_token: str, db: Session):
    check_admin_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.login_token = login_token
        db.commit()
        return user
    return None


def set_linked_account_to_user(token: str, user_name: str, account_ids: List[str], db: Session):
    check_admin_token(token)
    # First, get the user
    user = db.query(User).filter(User.name == user_name).first()
    if not user:
        return False

    # Delete existing links
    existing_links = db.query(UserAccountAssociation).filter(
        UserAccountAssociation.user_id == user.id).all()
    for link in existing_links:
        db.delete(link)

    # Create new links
    for account_id in account_ids:
        new_link = UserAccountAssociation(user_id=user.id, account_id=account_id)
        db.add(new_link)

    db.commit()
    return True


# Backend Utility Methods
def retrieve_strategy_balance(strategy: Strategy) -> float:
    exchange_class = getattr(ccxt, strategy.exchange_type.lower())
    exchange = exchange_class({
        'apiKey': strategy.api_key,
        'secret': strategy.secret_key,
        'password': strategy.passphrase
    })
    balance = exchange.fetch_balance()
    return balance['total']


def get_linked_accounts(user_name: str, db: Session):
    linked_accounts = db.query(UserAccountAssociation).filter(UserAccountAssociation.user_id == user_name).all()
    account_ids = [link.account_id for link in linked_accounts]
    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    return accounts


# def sum_balance_tables(balances: Dict) -> Dict:
#     total_preset_balance = sum(balance['preset_balance'] for balance in balances if 'preset_balance' in balance)
#     total_realtime_balance = sum(balance['realtime_balance'] for balance in balances if 'realtime_balance' in balance)
#     total_difference = total_realtime_balance - total_preset_balance
#     total_percentage_difference = (total_difference / total_preset_balance) * 100 if total_preset_balance else 0
#     return {
#         'total_preset_balance': total_preset_balance,
#         'total_realtime_balance': total_realtime_balance,
#         'total_difference': total_difference,
#         'total_percentage_difference': total_percentage_difference
#     }


# Scheduled Tasks with APScheduler

def daily_balance_snapshot(db: Session):
    accounts = db.query(Account).all()
    for account in accounts:
        strategies = db.query(Strategy).filter(Strategy.account_id == account.id).all()
        for strategy in strategies:
            strategy_balance = retrieve_strategy_balance(strategy)
            new_record = AccountBalanceHistory(
                account_id=str(account.id),
                strategy_id=str(strategy.id),
                balance=strategy_balance,
                timestamp=datetime.now()
            )
            db.add(new_record)
        logger.info(f"Daily balance snapshot taken for account {account.account_name}")
    db.commit()


def start_scheduler(hour=0, minute=0):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: daily_balance_snapshot(next(get_db())), 'cron', hour=hour, minute=minute)
    scheduler.start()
    logger.info(f"Scheduler started for every day at {hour}:{minute}")

# Uncomment the line below to start the scheduler when running this module
# start_scheduler()
