# database_manager.py
import sqlite3
import os
import logging
import base64
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# PostgreSQL support - try to import, but make it optional
try:
    import psycopg2
    from psycopg2 import sql
    POSTGRESQL_AVAILABLE = True
except ImportError:
    psycopg2 = None
    POSTGRESQL_AVAILABLE = False
    print("PostgreSQL support disabled. Install psycopg2-binary for PostgreSQL support.")

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.db_path = None
        self.is_connected = False
        self.cipher = None
        self.salt = None
        self.db_type = None  # 'sqlite' or 'postgresql'
        self.db_config = None
        logging.debug("Database manager initialized")
    
    def _derive_key(self, master_password: str) -> bytes:
        """Derive encryption key from master password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data"""
        if not data:
            return ""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logging.error(f"Encryption error: {str(e)}")
            return ""
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data"""
        if not encrypted_data:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            return self.cipher.decrypt(encrypted_bytes).decode()
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            return ""
    
    def _execute_sqlite(self, query: str, params: tuple = None) -> Any:
        """Execute SQLite query"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def _execute_postgresql(self, query: str, params: tuple = None) -> Any:
        """Execute PostgreSQL query"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def execute(self, query: str, params: tuple = None) -> Any:
        """Execute query based on database type"""
        if not self.is_connected:
            raise Exception("Database not connected")
        
        if self.db_type == 'sqlite':
            return self._execute_sqlite(query, params)
        else:
            return self._execute_postgresql(query, params)
    
    def _check_existing_data(self) -> bool:
        """Check if tables already exist and have data"""
        try:
            if self.db_type == 'sqlite':
                cursor = self.conn.cursor()
                # Check if passwords table exists and has data
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='passwords'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM passwords")
                    count = cursor.fetchone()[0]
                    return count > 0
            else:  # PostgreSQL
                cursor = self.conn.cursor()
                # Check if passwords table exists and has data
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'passwords'
                    )
                """)
                if cursor.fetchone()[0]:
                    cursor.execute("SELECT COUNT(*) FROM passwords")
                    count = cursor.fetchone()[0]
                    return count > 0
            return False
        except Exception as e:
            logging.error(f"Error checking existing data: {str(e)}")
            return False
    
    def _create_tables(self):
        """Create necessary tables for both SQLite and PostgreSQL"""
        try:
            # Check if tables already exist with data
            if self._check_existing_data():
                logging.info("Tables already exist with data, skipping table creation")
                return
            
            # Create metadata table first
            if self.db_type == 'sqlite':
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS _metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                ''')
                
                # Create folders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS folders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        icon BLOB,
                        color TEXT DEFAULT '#3498db',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create passwords table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS passwords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        folder_id INTEGER DEFAULT 1,
                        title_encrypted TEXT NOT NULL,
                        username_encrypted TEXT,
                        password_encrypted TEXT NOT NULL,
                        url_encrypted TEXT,
                        notes_encrypted TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET DEFAULT
                    )
                ''')
            else:  # PostgreSQL
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS _metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS folders (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        icon BYTEA,
                        color TEXT DEFAULT '#3498db',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS passwords (
                        id SERIAL PRIMARY KEY,
                        folder_id INTEGER DEFAULT 1,
                        title_encrypted TEXT NOT NULL,
                        username_encrypted TEXT,
                        password_encrypted TEXT NOT NULL,
                        url_encrypted TEXT,
                        notes_encrypted TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET DEFAULT
                    )
                ''')
            
            # Insert default folder only if it doesn't exist
            if self.db_type == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM folders WHERE id = 1")
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute('''
                        INSERT INTO folders (id, name, color) 
                        VALUES (1, 'General', '#3498db')
                    ''')
            else:
                cursor.execute("SELECT COUNT(*) FROM folders WHERE id = 1")
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute('''
                        INSERT INTO folders (id, name, color) 
                        VALUES (1, 'General', '#3498db')
                    ''')
            
            self.conn.commit()
            
        except Exception as e:
            logging.error(f"Error creating tables: {str(e)}")
            raise
    
    def create_sqlite_database(self, db_path: str, master_password: str) -> bool:
        """Create a new encrypted SQLite database"""
        try:
            logging.debug(f"Creating SQLite database at {db_path}")
            self.db_path = db_path
            self.db_type = 'sqlite'
            
            # Generate salt and create cipher
            self.salt = os.urandom(16)
            key = self._derive_key(master_password)
            self.cipher = Fernet(key)
            
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            
            # Create database
            self.conn = sqlite3.connect(db_path)
            
            # Store salt in metadata table
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS _metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            cursor.execute(
                "INSERT OR REPLACE INTO _metadata (key, value) VALUES (?, ?)",
                ('salt', base64.urlsafe_b64encode(self.salt).decode())
            )
            
            self.conn.commit()
            
            # Now create the tables
            self._create_tables()
            
            self.is_connected = True
            logging.info(f"SQLite database created successfully at {db_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating SQLite database: {str(e)}")
            if self.conn:
                self.conn.close()
                self.is_connected = False
            return False
    
    def create_postgresql_database(self, db_config: dict, master_password: str) -> bool:
        """Create a new encrypted PostgreSQL database"""
        if not POSTGRESQL_AVAILABLE:
            logging.error("PostgreSQL support not available. Install psycopg2-binary.")
            return False
            
        try:
            logging.debug(f"Creating PostgreSQL database connection")
            self.db_type = 'postgresql'
            self.db_config = db_config
            
            # Generate salt and create cipher
            self.salt = os.urandom(16)
            key = self._derive_key(master_password)
            self.cipher = Fernet(key)
            
            # Connect to PostgreSQL
            self.conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            
            # Store salt in metadata table
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS _metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            cursor.execute(
                "INSERT INTO _metadata (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                ('salt', base64.urlsafe_b64encode(self.salt).decode())
            )
            
            self.conn.commit()
            
            # Now create the tables (only if they don't exist with data)
            self._create_tables()
            
            self.is_connected = True
            logging.info(f"PostgreSQL database connected successfully: {db_config['database']}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating PostgreSQL database: {str(e)}")
            if self.conn:
                self.conn.close()
                self.is_connected = False
            return False
    
    def connect_sqlite_database(self, db_path: str, master_password: str) -> bool:
        """Connect to an existing SQLite database"""
        try:
            if not os.path.exists(db_path):
                logging.error("SQLite database file does not exist")
                return False
                
            self.db_path = db_path
            self.db_type = 'sqlite'
            self.conn = sqlite3.connect(db_path)
            cursor = self.conn.cursor()
            
            # Get salt from metadata
            cursor.execute("SELECT value FROM _metadata WHERE key = 'salt'")
            result = cursor.fetchone()
            if not result:
                logging.error("No encryption salt found")
                return False
                
            self.salt = base64.urlsafe_b64decode(result[0].encode())
            
            # Create cipher with derived key
            key = self._derive_key(master_password)
            self.cipher = Fernet(key)
            
            # Test encryption by reading a folder
            cursor.execute("SELECT COUNT(*) FROM folders")
            self.conn.commit()
            
            self.is_connected = True
            logging.info(f"Connected to SQLite database successfully: {db_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error connecting to SQLite database: {str(e)}")
            if self.conn:
                self.conn.close()
                self.is_connected = False
            return False
    
    def connect_postgresql_database(self, db_config: dict, master_password: str) -> bool:
        """Connect to an existing PostgreSQL database"""
        if not POSTGRESQL_AVAILABLE:
            logging.error("PostgreSQL support not available. Install psycopg2-binary.")
            return False
            
        try:
            self.db_type = 'postgresql'
            self.db_config = db_config
            
            # Connect to PostgreSQL
            self.conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            
            # Get salt from metadata
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM _metadata WHERE key = 'salt'")
            result = cursor.fetchone()
            if not result:
                logging.error("No encryption salt found")
                return False
                
            self.salt = base64.urlsafe_b64decode(result[0].encode())
            
            # Create cipher with derived key
            key = self._derive_key(master_password)
            self.cipher = Fernet(key)
            
            # Test encryption by reading a folder
            cursor.execute("SELECT COUNT(*) FROM folders")
            self.conn.commit()
            
            self.is_connected = True
            logging.info(f"Connected to PostgreSQL database successfully: {db_config['database']}")
            return True
            
        except Exception as e:
            logging.error(f"Error connecting to PostgreSQL database: {str(e)}")
            if self.conn:
                self.conn.close()
                self.is_connected = False
            return False
    
    # Folder Management Methods
    def create_folder(self, name: str, icon_data: bytes = None, color: str = "#3498db") -> int:
        """Create a new folder and return its ID"""
        if not self.is_connected:
            logging.error("Cannot create folder: Database not connected")
            return -1
            
        try:
            cursor = self.execute('''
                INSERT INTO folders (name, icon, color)
                VALUES (?, ?, ?)
            ''' if self.db_type == 'sqlite' else '''
                INSERT INTO folders (name, icon, color)
                VALUES (%s, %s, %s)
            ''', (name, icon_data, color))
            self.conn.commit()
            folder_id = cursor.lastrowid if self.db_type == 'sqlite' else cursor.fetchone()[0]
            logging.info(f"Folder created: {name} (ID: {folder_id})")
            return folder_id
        except Exception as e:
            logging.error(f"Error creating folder: {str(e)}")
            return -1
    
    def get_folders(self) -> List[Dict]:
        """Get all folders"""
        if not self.is_connected:
            logging.error("Cannot get folders: Database not connected")
            return []
            
        try:
            cursor = self.execute('''
                SELECT id, name, icon, color, created_at, updated_at
                FROM folders ORDER BY name
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            folders = []
            
            for row in cursor.fetchall():
                folder_data = dict(zip(columns, row))
                # Convert icon blob to base64 for easy handling in UI
                if folder_data.get('icon'):
                    folder_data['icon_base64'] = base64.b64encode(folder_data['icon']).decode('utf-8')
                else:
                    folder_data['icon_base64'] = None
                folders.append(folder_data)
                
            return folders
        except Exception as e:
            logging.error(f"Error retrieving folders: {str(e)}")
            return []
    
    def update_folder(self, folder_id: int, name: str = None, icon_data: bytes = None, 
                     color: str = None) -> bool:
        """Update folder properties"""
        if not self.is_connected:
            logging.error("Cannot update folder: Database not connected")
            return False
            
        try:
            update_fields = []
            params = []
            
            if name is not None:
                update_fields.append("name = ?" if self.db_type == 'sqlite' else "name = %s")
                params.append(name)
            if icon_data is not None:
                update_fields.append("icon = ?" if self.db_type == 'sqlite' else "icon = %s")
                params.append(icon_data)
            if color is not None:
                update_fields.append("color = ?" if self.db_type == 'sqlite' else "color = %s")
                params.append(color)
                
            update_fields.append("updated_at = ?" if self.db_type == 'sqlite' else "updated_at = %s")
            params.append(datetime.now())
            params.append(folder_id)
            
            if update_fields:
                query = f"UPDATE folders SET {', '.join(update_fields)} WHERE id = ?" if self.db_type == 'sqlite' else f"UPDATE folders SET {', '.join(update_fields)} WHERE id = %s"
                cursor = self.execute(query, params)
                self.conn.commit()
                logging.info(f"Folder updated: ID {folder_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating folder: {str(e)}")
            return False
    
    def delete_folder(self, folder_id: int, move_to_folder_id: int = 1) -> bool:
        """Delete a folder and move its passwords to another folder"""
        if not self.is_connected or folder_id == 1:  # Cannot delete default folder
            logging.error("Cannot delete folder: Database not connected or default folder")
            return False
            
        try:
            # Move passwords to another folder
            self.execute('''
                UPDATE passwords SET folder_id = ? WHERE folder_id = ?
            ''' if self.db_type == 'sqlite' else '''
                UPDATE passwords SET folder_id = %s WHERE folder_id = %s
            ''', (move_to_folder_id, folder_id))
            
            # Delete the folder
            self.execute('DELETE FROM folders WHERE id = ?' if self.db_type == 'sqlite' else 'DELETE FROM folders WHERE id = %s', (folder_id,))
            self.conn.commit()
            logging.info(f"Folder deleted: ID {folder_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting folder: {str(e)}")
            return False
    
    # Password Management Methods
    def add_password(self, title: str, username: str, password: str, 
                    folder_id: int = 1, url: str = "", notes: str = "") -> bool:
        """Add a new password entry to a specific folder"""
        if not self.is_connected:
            logging.error("Cannot add password: Database not connected")
            return False
            
        try:
            logging.debug(f"Adding password: {title} to folder {folder_id}")
            cursor = self.execute('''
                INSERT INTO passwords (folder_id, title_encrypted, username_encrypted, 
                                    password_encrypted, url_encrypted, notes_encrypted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''' if self.db_type == 'sqlite' else '''
                INSERT INTO passwords (folder_id, title_encrypted, username_encrypted, 
                                    password_encrypted, url_encrypted, notes_encrypted)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (folder_id, 
                  self.encrypt_data(title),
                  self.encrypt_data(username),
                  self.encrypt_data(password),
                  self.encrypt_data(url),
                  self.encrypt_data(notes)))
            self.conn.commit()
            logging.info(f"Password added to folder {folder_id}: {title}")
            return True
        except Exception as e:
            logging.error(f"Error adding password: {str(e)}")
            return False
    
    def get_passwords(self, folder_id: int = None) -> List[Dict]:
        """Get all passwords, optionally filtered by folder"""
        if not self.is_connected:
            logging.error("Cannot get passwords: Database not connected")
            return []
            
        try:
            if folder_id:
                cursor = self.execute('''
                    SELECT p.id, p.folder_id, p.title_encrypted, p.username_encrypted, 
                           p.password_encrypted, p.url_encrypted, p.notes_encrypted,
                           p.created_at, p.updated_at, f.name as folder_name
                    FROM passwords p
                    LEFT JOIN folders f ON p.folder_id = f.id
                    WHERE p.folder_id = ? 
                    ORDER BY p.title_encrypted
                ''' if self.db_type == 'sqlite' else '''
                    SELECT p.id, p.folder_id, p.title_encrypted, p.username_encrypted, 
                           p.password_encrypted, p.url_encrypted, p.notes_encrypted,
                           p.created_at, p.updated_at, f.name as folder_name
                    FROM passwords p
                    LEFT JOIN folders f ON p.folder_id = f.id
                    WHERE p.folder_id = %s 
                    ORDER BY p.title_encrypted
                ''', (folder_id,))
            else:
                cursor = self.execute('''
                    SELECT p.id, p.folder_id, p.title_encrypted, p.username_encrypted, 
                           p.password_encrypted, p.url_encrypted, p.notes_encrypted,
                           p.created_at, p.updated_at, f.name as folder_name
                    FROM passwords p
                    LEFT JOIN folders f ON p.folder_id = f.id
                    ORDER BY f.name, p.title_encrypted
                ''')
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                # Decrypt the data
                row_dict['title'] = self.decrypt_data(row_dict.pop('title_encrypted'))
                row_dict['username'] = self.decrypt_data(row_dict.pop('username_encrypted'))
                row_dict['password'] = self.decrypt_data(row_dict.pop('password_encrypted'))
                row_dict['url'] = self.decrypt_data(row_dict.pop('url_encrypted'))
                row_dict['notes'] = self.decrypt_data(row_dict.pop('notes_encrypted'))
                results.append(row_dict)
                
            return results
        except Exception as e:
            logging.error(f"Error retrieving passwords: {str(e)}")
            return []
    
    def update_password(self, entry_id: int, title: str = None, username: str = None, 
                       password: str = None, url: str = None, notes: str = None, 
                       folder_id: int = None) -> bool:
        """Update a password entry"""
        if not self.is_connected:
            return False
            
        try:
            update_fields = []
            params = []
            
            if title is not None:
                update_fields.append("title_encrypted = ?" if self.db_type == 'sqlite' else "title_encrypted = %s")
                params.append(self.encrypt_data(title))
            if username is not None:
                update_fields.append("username_encrypted = ?" if self.db_type == 'sqlite' else "username_encrypted = %s")
                params.append(self.encrypt_data(username))
            if password is not None:
                update_fields.append("password_encrypted = ?" if self.db_type == 'sqlite' else "password_encrypted = %s")
                params.append(self.encrypt_data(password))
            if url is not None:
                update_fields.append("url_encrypted = ?" if self.db_type == 'sqlite' else "url_encrypted = %s")
                params.append(self.encrypt_data(url))
            if notes is not None:
                update_fields.append("notes_encrypted = ?" if self.db_type == 'sqlite' else "notes_encrypted = %s")
                params.append(self.encrypt_data(notes))
            if folder_id is not None:
                update_fields.append("folder_id = ?" if self.db_type == 'sqlite' else "folder_id = %s")
                params.append(folder_id)
                
            update_fields.append("updated_at = ?" if self.db_type == 'sqlite' else "updated_at = %s")
            params.append(datetime.now())
            params.append(entry_id)
            
            if update_fields:
                query = f"UPDATE passwords SET {', '.join(update_fields)} WHERE id = ?" if self.db_type == 'sqlite' else f"UPDATE passwords SET {', '.join(update_fields)} WHERE id = %s"
                cursor = self.execute(query, params)
                self.conn.commit()
                logging.info(f"Password updated: ID {entry_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error updating password: {str(e)}")
            return False
    
    def delete_password(self, entry_id: int) -> bool:
        """Delete a password entry"""
        if not self.is_connected:
            return False
            
        try:
            self.execute('DELETE FROM passwords WHERE id = ?' if self.db_type == 'sqlite' else 'DELETE FROM passwords WHERE id = %s', (entry_id,))
            self.conn.commit()
            logging.info(f"Password deleted: ID {entry_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting password: {str(e)}")
            return False
    
    def search_passwords(self, search_term: str) -> List[Dict]:
        """Search passwords by title, username, or url"""
        if not self.is_connected:
            return []
            
        try:
            all_passwords = self.get_passwords()
            results = []
            
            for pwd in all_passwords:
                if (search_term.lower() in pwd['title'].lower() or 
                    search_term.lower() in (pwd['username'] or '').lower() or 
                    search_term.lower() in (pwd['url'] or '').lower() or
                    search_term.lower() in pwd['folder_name'].lower()):
                    results.append(pwd)
                    
            return results
        except Exception as e:
            logging.error(f"Error searching passwords: {str(e)}")
            return []
    
    def get_password_count_by_folder(self) -> List[Dict]:
        """Get password count for each folder"""
        if not self.is_connected:
            return []
            
        try:
            cursor = self.execute('''
                SELECT f.id, f.name, f.color, COUNT(p.id) as password_count
                FROM folders f
                LEFT JOIN passwords p ON f.id = p.folder_id
                GROUP BY f.id, f.name, f.color
                ORDER BY f.name
            ''')
            
            return [dict(zip(['id', 'name', 'color', 'password_count'], row)) 
                   for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Error getting password counts: {str(e)}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.is_connected = False
        logging.info("Database connection closed")