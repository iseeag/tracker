# Asset Tracker App Requirements

Develop an asset tracker application using **Gradio** with the following structure:

- **Frontend**: `gr_app.py`
- **Backend**: `gr_backend.py`
- **Database**: `gr_db.py`

## Overview

The application will have two main user roles:

1. **Administrator**: Manages accounts, strategies, and users.
2. **User**: Views linked account balances and history.

---

## Administrator Interface

### Authentication

- **Login**:
	- The administrator logs in using a **master token**.
	- Upon successful login, an authentication token is saved to the session state.
- **Logout**:
	- Clears the session state to log out.
- **Notes**:
	- No registration process is needed.
	- There is only **one admin account**.
	- The **hash of the master token** is stored in a `.env` file for security.

### Account Management

- **CRUD Operations**:
	- **Add**, **Delete**, and **Update** accounts.
- **Account Details**:
	- **Account Name**: A unique identifier for the account.
	- **Start Date**: The date when the account became active.
	- **Strategies**: Each account can have multiple strategies.
		- **Strategy Name**
		- **API Key**
		- **Secret Key**
		- **Passphrase** (if required by the exchange)
		- **Exchange Type**: e.g., Bitget or Binance
		- **Preset Balance**: The initial or expected balance.
- **Verification**:
	- After adding an account, verify the account information (e.g., test API keys to ensure they are valid).

### User Management

- **CRUD Operations**:
	- **Add**, **Delete**, and **Update** users.
- **User Details**:
	- **Name**: The user's name.
	- **Login Token**: Used for user authentication.
	- **Linked Accounts**: Accounts accessible by the user.
		- Use checkboxes to select and edit linked accounts.

---

## User Interface

### Authentication

- **Login**:
	- Users log in using their **login token**.
	- Upon successful login, an authentication token is saved to the session state.
- **Logout**:
	- Clears the session state to log out.
- **Notes**:
	- No registration process is needed.

### Dashboard

- **Summarized Balance Tables**:
	- Display a **summed Preset Balance Table** of all linked accounts.
	- Display a **summed Realtime Balance Table** of all linked accounts.
- **Individual Account Details**:
	- For each linked account, display:
		- **Preset Balance Table**
		- **Realtime Balance Table**
		- **Account Balance History Table** with pagination controls.

---

## Backend Specifications

### General

- Use **PostgreSQL (pg)** to store all data.
	- Database credentials are stored securely in a `.env` file.

### Database Schema

1. **Accounts Table**:
	- `account_name` (Primary Key)
	- `start_date`
2. **Strategies Table**:
	- `account_name` (Foreign Key to Accounts Table)
	- `strategy_name`
	- `api_key`
	- `secret_key`
	- `passphrase` (if applicable)
	- `exchange_type` (e.g., Bitget, Binance)
	- `preset_balance`
3. **Users Table**:
	- `name` (Primary Key)
	- `login_token`
4. **User_Accounts Table**:
	- `user_name` (Foreign Key to Users Table)
	- `account_name` (Foreign Key to Accounts Table)
5. **Account_Balance_History Table**:
	- `account_name` (Foreign Key to Accounts Table)
	- `strategy_name`
	- `balance`
	- `timestamp`

### Authentication Logic

- **Session Management**:
	- Upon login, generate and maintain a **session token** for both admin and user types.
	- Upon logout, **clear the session token**.

### API Endpoints (Frontend-Facing Methods)

- **Authentication Required**: All methods require a valid session token.

#### User-Type Methods

- **Get Preset Balance Tables**:
	- Returns preset balance tables for all accounts linked to the user.
- **Get Realtime Balance Tables**:
	- Returns realtime balance tables for all linked accounts.
	- Utilizes **CCXT** to fetch real-time data from exchanges.
- **Get Account Balance History Tables**:
	- Returns balance history for linked accounts.
	- Supports pagination (default page number is 1).

#### Admin-Type Methods

- **Account and Strategy Management**:
	- Create, Read, Update, Delete (CRUD) operations on accounts and strategies.
- **User Management**:
	- CRUD operations on user information, including linking accounts.

### Backend Utility Methods

- **Get Linked Accounts**:
	- Given a username, return a list of accounts linked to the user.
- **Get Account Information**:
	- Given a list of account names, return detailed account information.
- **Sum Balance Tables**:
	- Aggregate multiple balance tables to provide summarized totals.

### Scheduled Tasks

- **Daily Balance Snapshot**:
	- Schedule a task to run **daily at 00:00:00**.
	- Fetch and save the realtime balance of all accounts to the **Account_Balance_History Table**.

---

## Frontend Table Structures

### 1. Preset Balance Table

**Purpose**: Display the expected balances for accounts and strategies.

**Columns**:

- **Account Name**
- **Strategy Name**
- **Preset Balance**

**Footer**:

- **Total Preset Balance**: Sum of all preset balances displayed.

### 2. Realtime Balance Table

**Purpose**: Display the current balances and compare them to the preset balances.

**Columns**:

- **Account Name**
- **Strategy Name**
- **Realtime Balance**
- **Difference**: Realtime Balance - Preset Balance
- **Percentage Difference**: (Difference / Preset Balance) * 100%

**Footer**:

- **Total Realtime Balance**
- **Total Difference**
- **Total Percentage Difference**

### 3. Account Balance History Table

**Purpose**: Display historical balance data for accounts over time.

**Columns**:

- **Date**
- **Strategy Balances**:
	- **Strategy 1 Balance**
	- **Strategy 2 Balance**
	- ...
	- **Total Balance**
- **Difference from Previous Entry**:
	- **Strategy 1 Difference**
	- **Strategy 2 Difference**
	- ...
	- **Total Balance Difference**
- **Percentage Difference**:
	- **Strategy 1 % Difference**
	- **Strategy 2 % Difference**
	- ...
	- **Total % Difference**

**Features**:

- **Pagination**: Navigate through historical data pages.
- **Sorting**: Ability to sort by date or balance columns.
- **Filtering**: Optionally filter by date range.
