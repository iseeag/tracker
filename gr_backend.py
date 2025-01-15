import hashlib
import os
import uuid
from datetime import datetime
from typing import Dict, List, Tuple

import ccxt
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy.orm import Session

from gr_db import (Account, AccountBalanceHistory, AccountBalances,
                   SessionLocal, Strategy, StrategyBalance,
                   StrategyBalanceRecord, User, UserAccountAssociation)

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
    linked_acc_ids = db.query(UserAccountAssociation).filter(UserAccountAssociation.user_id == user_id).all()
    account_ids = [link.account_id for link in linked_acc_ids]
    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    account_names = [a.account_name for a in accounts]
    strategies = db.query(Strategy).filter(Strategy.account_name.in_(account_names)).all()
    return accounts, strategies


def get_tables(token: str, date_ranges: Dict[str, Tuple[str, str]], db: Session) -> Dict:
    """
     {"summarized_preset": pd.DataFrame(),
      "summarized_realtime": pd.DataFrame(),
      "linked_accounts": [{
          'name': 'account',
          'start_date': '2025-01-01',
          "preset": pd.DataFrame(),
          "realtime": pd.DataFrame(),
          "history": {'start_date': '2025-01-01',
                      'end_date': '2026-01-01',
                      'data': pd.DataFrame()},
      }]}
    """
    logger.info(f"Getting balance tables")
    user_id = get_user_id(token)
    accounts, strategies = retrieve_multi_info(user_id, db)
    account_ids = [account.id for account in accounts]
    account_names = [str(account.account_name) for account in accounts]
    date_str_ranges = date_ranges
    date_ranges = {account_name: (datetime.strptime(s, "%Y-%m-%d").date(),
                                  datetime.strptime(e, "%Y-%m-%d").date())
                   for account_name, (s, e) in date_str_ranges.items()}
    strategy_id_name = {s.id: s.strategy_name for s in strategies}
    account_balance_history = [db.query(AccountBalanceHistory).filter(
        AccountBalanceHistory.timestamp >= date_ranges[account_name][0],
        AccountBalanceHistory.timestamp <= date_ranges[account_name][1],
        AccountBalanceHistory.account_id == account_id
    ).all() for account_id, account_name in zip(account_ids, account_names)]

    account_balances = [AccountBalances(
        name=str(account.account_name),
        start_date=str(account.start_date),
        preset_balances=[
            StrategyBalance(
                name=str(strategy.strategy_name),
                balance=float(strategy.preset_balance),
            ) for strategy in strategies if strategy.account_name == account.account_name],
        realtime_balances=[
            StrategyBalance(
                name=str(strategy.strategy_name),
                balance=retrieve_strategy_balance(strategy),
            ) for strategy in strategies if strategy.account_name == account.account_name],
        strategy_balance_records=[
            StrategyBalanceRecord(
                name=str(strategy_id_name[record.strategy_id]),
                balance=float(record.balance),
                timestamp=record.timestamp
            ) for record in account_histories
        ],
        record_start_date=date_str_ranges[str(account.account_name)][0],
        record_end_date=date_str_ranges[str(account.account_name)][1]
    ) for account, account_histories in zip(accounts, account_balance_history)]

    return {"summarized": AccountBalances.sum_df(account_balances),
            "linked_accounts": [{
                "name": str(account.name),
                "start_date": str(account.start_date),
                "data": account.account_df,
                "history": {
                    "start_date": account.record_start_date,
                    "end_date": account.record_end_date,
                    "data": account.record_df,
                }
            } for account in account_balances]}


def check_admin_token(token: str):
    if current_session_tokens.get('admin') != token:
        raise Exception("Unauthorized access")


def create_account(token: str, account_name: str, start_date: str, db: Session):
    check_admin_token(token)
    new_account = Account(
        account_name=account_name,
        start_date=datetime.strptime(start_date, "%Y-%m-%d").date()
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)  # Refresh to get the auto-generated ID
    logger.info(f"Created account {account_name}")
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
        strategies = db.query(Strategy).filter(Strategy.account_name == account_name).all()
        for strategy in strategies:
            db.delete(strategy)
        db.commit()
        logger.info(f"Deleted account {account_name} and its strategies and associations")
        return True
    return False


def update_account(token: str, account_name: str, start_date: str, db: Session):
    check_admin_token(token)
    account = db.query(Account).filter(Account.account_name == account_name).first()
    if account:
        account.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        db.commit()
        logger.info(f"Updated account {account_name}")
        return account
    logger.warning(f"Account {account_name} not found, update failed")
    return None


def get_account(token: str, account_name: str, db: Session):
    check_admin_token(token)
    account = db.query(Account).filter(Account.account_name == account_name).first()
    return account


def list_accounts(token: str, db: Session):
    check_admin_token(token)
    accounts = db.query(Account).all()
    return accounts


def list_user_linked_accounts(token: str, db: Session):
    user_id = get_user_id(token)
    user = db.query(User).filter(User.id == user_id).first()
    linked_accounts = get_user_linked_accounts(user.name, db)
    return linked_accounts


def create_strategy(token: str, account_name: str, strategy_name: str, api_key: str, secret_key: str, passphrase: str,
                    exchange_type: str, preset_balance: float, db: Session):
    check_admin_token(token)
    new_strategy = Strategy(
        account_name=account_name,
        strategy_name=strategy_name,
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        exchange_type=exchange_type,
        preset_balance=preset_balance
    )
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    logger.info(f"Created strategy {strategy_name}")
    return new_strategy


def get_strategy(token: str, account_name, strategy_name: str, db: Session):
    check_admin_token(token)
    strategy = db.query(Strategy).filter(Strategy.account_name == account_name,
                                         Strategy.strategy_name == strategy_name).first()
    return strategy


def delete_strategy(token: str, account_name: str, strategy_name: str, db: Session):
    check_admin_token(token)
    strategy = get_strategy(token, account_name, strategy_name, db)
    if strategy:
        db.delete(strategy)
        db.commit()
        logger.info(f"Deleted strategy {strategy_name}")
        return True
    logger.warning(f"Strategy {strategy_name} not found, deletion failed")
    return False


def update_strategy(token: str, account_name: str, strategy_name: str, api_key: str,
                    secret_key: str, passphrase: str, exchange_type: str, preset_balance: float, db: Session):
    check_admin_token(token)
    strategy = get_strategy(token, account_name, strategy_name, db)
    if strategy:
        strategy.api_key = api_key
        strategy.secret_key = secret_key
        strategy.passphrase = passphrase
        strategy.exchange_type = exchange_type
        strategy.preset_balance = preset_balance
        db.commit()
        return strategy
    return None


def validate_exchange_credentials(exchange_type: str, api_key: str, secret_key: str, passphrase: str = None) -> bool:
    """
    Validate exchange API credentials by attempting to fetch balance.
    
    Args:
        exchange_type: The type of exchange (e.g., 'bitget', 'binance')
        api_key: Exchange API key
        secret_key: Exchange secret key
        passphrase: Exchange passphrase (required for some exchanges like Bitget)
    
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        exchange_class = getattr(ccxt, exchange_type.lower())
        config = {'apiKey': api_key, 'secret': secret_key}
        if passphrase:
            config['password'] = passphrase
        exchange = exchange_class(config)
        exchange.fetch_balance()
        logger.info(f"{exchange_type.capitalize()} credentials validation successful")
        return True

    except AttributeError:
        logger.error(f"Unsupported exchange type: {exchange_type}")
        return False
    except Exception as e:
        logger.error(f"{exchange_type.capitalize()} credentials validation failed: {str(e)}")
        return False


# User Management

def create_user(token: str, name: str, login_token: str, linked_account_names: List[str], db: Session):
    check_admin_token(token)
    new_user = User(name=name, login_token=login_token)
    db.add(new_user)
    db.commit()
    logger.info(f"Created user {name}")
    linked_accounts = db.query(Account).filter(Account.account_name.in_(linked_account_names)).all()
    set_user_linked_account(token, name, [int(account.id) for account in linked_accounts], db)
    logger.info(f"Linked accounts {linked_account_names} to user {name}")
    return new_user


def get_user(token: str, name: str, db: Session):
    check_admin_token(token)
    user = db.query(User).filter(User.name == name).first()
    return user


def list_users(token: str, db: Session):
    check_admin_token(token)
    users = db.query(User).all()
    return users


def delete_user(token: str, name: str, db: Session):
    check_admin_token(token)
    user = db.query(User).filter(User.name == name).first()
    if user:
        # Delete all user-account associations
        user_account_links = db.query(UserAccountAssociation).filter(
            UserAccountAssociation.user_id == user.id).all()
        for link in user_account_links:
            db.delete(link)
        # Delete the user
        db.delete(user)
        db.commit()
        logger.info(f"Deleted user {name} and its associations")
        return True
    logger.warning(f"User {name} not found, deletion failed")
    return False


def update_user(token: str, name: str, login_token: str, linked_account_names: List[str], db: Session):
    check_admin_token(token)
    user = db.query(User).filter(User.name == name).first()
    if not user:
        logger.warning(f"User {name} not found, update failed")
        return None
    user.login_token = login_token
    linked_accounts = db.query(Account).filter(Account.account_name.in_(linked_account_names)).all()
    set_user_linked_account(token, name, [int(account.id) for account in linked_accounts], db)
    db.commit()
    logger.info(f"Updated user {name}")
    return user


def set_user_linked_account(token: str, user_name: str, account_ids: List[int], db: Session):
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
        new_link = UserAccountAssociation(user_id=int(user.id), account_id=int(account_id))
        db.add(new_link)

    logger.info(f"Linked accounts {account_ids} to user {user_name}")
    db.commit()
    return True


# Backend Utility Methods
def _get_usdt_value_via_cross(currency, amount, exchange, markets):
    btc_pair = f"{currency}/BTC"
    btc_usdt_pair = "BTC/USDT"
    if btc_pair in markets and btc_usdt_pair in markets:
        ticker_currency_btc = exchange.fetch_ticker(btc_pair)
        ticker_btc_usdt = exchange.fetch_ticker(btc_usdt_pair)
        price_currency_btc = ticker_currency_btc['last']
        price_btc_usdt = ticker_btc_usdt['last']
        usdt_value = amount * price_currency_btc * price_btc_usdt
        return usdt_value
    eth_pair = f"{currency}/ETH"
    eth_usdt_pair = "ETH/USDT"
    if eth_pair in markets and eth_usdt_pair in markets:
        ticker_currency_eth = exchange.fetch_ticker(eth_pair)
        ticker_eth_usdt = exchange.fetch_ticker(eth_usdt_pair)
        price_currency_eth = ticker_currency_eth['last']
        price_eth_usdt = ticker_eth_usdt['last']
        usdt_value = amount * price_currency_eth * price_eth_usdt
        return usdt_value
    return None


def _sum_coin_to_usdt(exchange: ccxt.Exchange) -> float:
    markets = exchange.load_markets()
    balance = exchange.fetch_balance()
    non_zero_balances = {
        currency: amounts
        for currency, amounts in balance['total'].items()
        if amounts > 0
    }
    total_usdt_value = 0.0
    prices = {}
    for currency in non_zero_balances:
        amount = balance['total'][currency]
        if currency == 'USDT':
            usdt_value = amount
        else:
            symbol = f"{currency}/USDT"
            if symbol in markets:
                ticker = exchange.fetch_ticker(symbol)
                last_price = ticker['last']
                usdt_value = amount * last_price
            else:
                logger.info("Market pair {symbol} not available. Trying alternative methods for {currency}...")
                usdt_value = _get_usdt_value_via_cross(currency, amount, exchange, markets)
                if usdt_value is None:
                    logger.warning(f"Unable to value {currency} in USDT.")
                    continue
        prices[currency] = usdt_value
        total_usdt_value += usdt_value
    logger.info(f"Total Balance in USDT: {total_usdt_value:.2f}")
    return total_usdt_value


def retrieve_strategy_balance(strategy: Strategy) -> float:
    try:
        exchange_class = getattr(ccxt, strategy.exchange_type.lower())
        exchange = exchange_class({
            'apiKey': strategy.api_key,
            'secret': strategy.secret_key,
            'password': strategy.passphrase
        })
        balance = _sum_coin_to_usdt(exchange)
    except Exception as e:
        logger.error(f"Failed to retrieve balance for {strategy.strategy_name}: {str(e)}")
        return float('nan')
    return balance


def get_user_linked_accounts(user_name: str, db: Session):
    user = db.query(User).filter(User.name == user_name).first()
    linked_accounts = db.query(UserAccountAssociation).filter(UserAccountAssociation.user_id == user.id).all()
    account_ids = [link.account_id for link in linked_accounts]
    accounts = db.query(Account).filter(Account.id.in_(account_ids)).all()
    return accounts


# Scheduled Tasks with APScheduler

def daily_balance_snapshot(db: Session):
    accounts = db.query(Account).all()
    for account in accounts:
        strategies = db.query(Strategy).filter(Strategy.account_name == account.account_name).all()
        for strategy in strategies:
            strategy_balance = retrieve_strategy_balance(strategy)
            new_record = AccountBalanceHistory(
                account_id=int(account.id),
                strategy_id=int(strategy.id),
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
