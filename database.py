import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import bcrypt

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create credentials table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS binance_credentials (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            api_key VARCHAR(255) NOT NULL,
            api_secret VARCHAR(255) NOT NULL,
            initial_value_usd DECIMAL(20, 2) NOT NULL,
            label VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, label)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

class UserManager:
    @staticmethod
    def create_user(username: str, password: str) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            password_hash = hash_password(password)
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def verify_user(username: str, password: str) -> dict:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and verify_password(password, user['password_hash']):
            return dict(user)
        return None

class CredentialManager:
    @staticmethod
    def add_credential(user_id: int, api_key: str, api_secret: str, 
                      initial_value_usd: float, label: str) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO binance_credentials 
                   (user_id, api_key, api_secret, initial_value_usd, label)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, api_key, api_secret, initial_value_usd, label)
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_credentials(user_id: int) -> list:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM binance_credentials WHERE user_id = %s",
            (user_id,)
        )
        credentials = cur.fetchall()
        cur.close()
        conn.close()
        return credentials
    
    @staticmethod
    def update_credential(cred_id: int, user_id: int, api_key: str, 
                         api_secret: str, initial_value_usd: float, label: str) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """UPDATE binance_credentials 
                   SET api_key = %s, api_secret = %s, 
                       initial_value_usd = %s, label = %s
                   WHERE id = %s AND user_id = %s""",
                (api_key, api_secret, initial_value_usd, label, cred_id, user_id)
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def delete_credential(cred_id: int, user_id: int) -> bool:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM binance_credentials WHERE id = %s AND user_id = %s",
                (cred_id, user_id)
            )
            conn.commit()
            return True
        except psycopg2.Error:
            return False
        finally:
            cur.close()
            conn.close()
