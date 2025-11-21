# settings_manager.py
import os
import json
import sqlite3
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SettingsManager:
    def __init__(self):
        self.settings_file = "settings.db"
        self.salt = b'prasword_salt_123456789012'  # Fixed salt for settings encryption
        self.init_database()
        
    def _derive_key(self, master_password: str) -> bytes:
        """Derive encryption key from master password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    
    def _encrypt_data(self, data: str, master_password: str) -> str:
        """Encrypt data with master password"""
        key = self._derive_key(master_password)
        cipher = Fernet(key)
        encrypted = cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str, master_password: str) -> str:
        """Decrypt data with master password"""
        try:
            key = self._derive_key(master_password)
            cipher = Fernet(key)
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = cipher.decrypt(encrypted_bytes).decode()
            return decrypted
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def init_database(self):
        """Initialize SQLite database for settings"""
        try:
            conn = sqlite3.connect(self.settings_file)
            cursor = conn.cursor()
            
            # Create databases table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS databases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    config_encrypted TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create app_settings table for future use
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            print(f"Settings database initialized: {self.settings_file}")
            
        except Exception as e:
            print(f"Error initializing settings database: {e}")
    
    def save_database_settings(self, databases: list, master_password: str) -> bool:
        """Save database configurations to SQLite database"""
        try:
            conn = sqlite3.connect(self.settings_file)
            cursor = conn.cursor()
            
            # Clear existing databases
            cursor.execute("DELETE FROM databases")
            
            # Insert each database
            for db in databases:
                # Encrypt the database config
                config_json = json.dumps(db)
                encrypted_config = self._encrypt_data(config_json, master_password)
                
                cursor.execute(
                    "INSERT INTO databases (name, type, config_encrypted) VALUES (?, ?, ?)",
                    (db['name'], db['type'], encrypted_config)
                )
            
            conn.commit()
            conn.close()
            print(f"Saved {len(databases)} databases to settings")
            return True
            
        except Exception as e:
            print(f"Error saving database settings: {e}")
            return False
    
    def load_database_settings(self, master_password: str) -> list:
        """Load database configurations from SQLite database"""
        try:
            if not os.path.exists(self.settings_file):
                print(f"Settings database {self.settings_file} does not exist")
                return []
                
            conn = sqlite3.connect(self.settings_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name, type, config_encrypted FROM databases")
            rows = cursor.fetchall()
            conn.close()
            
            databases = []
            for name, db_type, encrypted_config in rows:
                try:
                    # Decrypt the config
                    decrypted_config = self._decrypt_data(encrypted_config, master_password)
                    if decrypted_config is None:
                        print(f"Failed to decrypt database {name} - invalid password")
                        continue
                    
                    db_data = json.loads(decrypted_config)
                    databases.append(db_data)
                    
                except Exception as e:
                    print(f"Error processing database {name}: {e}")
                    continue
            
            print(f"Loaded {len(databases)} databases from settings")
            return databases
            
        except Exception as e:
            print(f"Error loading database settings: {e}")
            return None
    
    def add_database(self, db_config: dict, master_password: str) -> bool:
        """Add a new database configuration"""
        try:
            # Load existing databases
            existing_dbs = self.load_database_settings(master_password)
            if existing_dbs is None:
                # Invalid password, start fresh
                existing_dbs = []
            
            # Check if database already exists
            for db in existing_dbs:
                if db['name'] == db_config['name']:
                    return False  # Database with same name already exists
            
            # Add new database and save all
            existing_dbs.append(db_config)
            return self.save_database_settings(existing_dbs, master_password)
            
        except Exception as e:
            print(f"Error adding database: {e}")
            return False
    
    def remove_database(self, db_name: str, master_password: str) -> bool:
        """Remove a database configuration"""
        try:
            databases = self.load_database_settings(master_password)
            if databases is None:
                return False
            
            # Filter out the database to remove
            databases = [db for db in databases if db['name'] != db_name]
            return self.save_database_settings(databases, master_password)
            
        except Exception as e:
            print(f"Error removing database: {e}")
            return False
    
    def get_database(self, db_name: str, master_password: str) -> dict:
        """Get specific database configuration"""
        databases = self.load_database_settings(master_password)
        if databases is None:
            return None
            
        for db in databases:
            if db['name'] == db_name:
                return db
        return None
    
    def settings_file_exists(self) -> bool:
        """Check if settings database exists and has databases"""
        if not os.path.exists(self.settings_file):
            return False
            
        try:
            conn = sqlite3.connect(self.settings_file)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM databases")
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except:
            return False
    
    def get_database_count(self) -> int:
        """Get number of saved databases"""
        if not os.path.exists(self.settings_file):
            return 0
            
        try:
            conn = sqlite3.connect(self.settings_file)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM databases")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0