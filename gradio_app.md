# gradio asset tracker app requirements

## Administrator Tab

- auth
	- login with master token (then save auth token to session state)
	- logout (clear session state)
		- no registration needed
	- only one admin account
	- hash of master token is stored in .env file
- account management
	- add/delete/update account
	- each account has the following fields:
	- one account name, a start date
	- multiple strategies, each with strategy name, api-key, secret-key, balance (preset balance)
	- verify account info after adding account
- user management
	- add/delete/update user
	- user has: name, login token and linked accounts (use check box to edit linked accounts)

## User Tab

- auth
	- login with token (then save auth token to session state)
	- logout (clear session state)
		- no registration needed
- display a summed `account balance table` for all linked accounts
- display linked accounts one by one
	- a `preset balance table`
  - a `realtime balance table`
  - a `account balance history table` with pagination

## Monolith Backend

- use pg to store data, credentials in .env file
	- account table: account name, start date
	- strategy table: account name, strategy name, api-key, secret-key, balance
	- user table: name, login token, linked accounts
- login: generate and keep a session token for login (admin type and user type)
- logout: clear session token
- each frontend facing methods(require session token):
	- for user type frontend
		- return all linked preset account balance tables given session token
		- return all linked realtime account balance tables given session token
		- return all linked account balance history tables given session token and page number (default to 1)
	- for admin type frontend
		- curd account and strategy info to database
		- curd user info to database
- base methods
	- return list of linked accounts given username
	- return list of account info given list of account names
	- return list of preset account balance tables given list of account names
	- return list of realtime account balance tables given list of account names (using ccxt to fetch data)
	- return list of account balance history tables given list of account name and page number
	- method to sum multiple account balance tables
- schedule: every day at 00:00:00, save all realtime account balance to history table

### Account Balance Table Frontend Structure

Create from preset balance table and realtime balance table:

1. preset balance table shows: account name, strategy name, preset balance, total preset balance
2. realtime balance table shows: account name, strategy name, real balance, difference between
   real balance and preset balance, percentage difference between real balance and preset balance

### Account balance history table Frontend Structure

history table will need to show all strategies in one row, therefore shows columns: date, strategy1 balance, strategy2
balance, ..., total balance, strategy1 balance difference,strategy2 balance difference, ..., total balance difference,
strategy1 balance percentage difference, strategy2 balance percentage difference, ..., total balance percentage
difference