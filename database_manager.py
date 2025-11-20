# database_manager.py
import sqlite3
import os
import logging
import base64
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class LocalDatabaseManager:
    def __init__(self):
        self.conn = None
        self.db_path = None
        self.is_connected = False
        self.cipher = None
        self.salt = None
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
    
    def create_database(self, db_path: str, master_password: str) -> bool:
        """Create a new encrypted database"""
        try:
            logging.debug(f"Creating database at {db_path}")
            self.db_path = db_path
            
            # Generate salt and create cipher
            self.salt = os.urandom(16)
            key = self._derive_key(master_password)
            self.cipher = Fernet(key)
            
            # Create database
            self.conn = sqlite3.connect(db_path)
            cursor = self.conn.cursor()
            
            # Store salt in a separate table
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
            
            # Create passwords table with encrypted fields
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
            
            # Insert default folder
            cursor.execute('''
                INSERT OR IGNORE INTO folders (id, name, color) 
                VALUES (1, 'General', '#3498db')
            ''')
            
            self.conn.commit()
            self.is_connected = True
            logging.info(f"Database created successfully at {db_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating database: {str(e)}")
            if self.conn:
                self.conn.close()
            return False
    
    def connect_database(self, db_path: str, master_password: str) -> bool:
        """Connect to an existing encrypted database"""
        try:
            if not os.path.exists(db_path):
                logging.error("Database file does not exist")
                return False
                
            self.db_path = db_path
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
            logging.info(f"Connected to database successfully: {db_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error connecting to database: {str(e)}")
            if self.conn:
                self.conn.close()
            return False
    
    # Folder Management Methods
    def create_folder(self, name: str, icon_data: bytes = None, color: str = "#3498db") -> int:
        """Create a new folder and return its ID"""
        if not self.is_connected:
            logging.error("Cannot create folder: Database not connected")
            return -1
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO folders (name, icon, color)
                VALUES (?, ?, ?)
            ''', (name, icon_data, color))
            self.conn.commit()
            folder_id = cursor.lastrowid
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
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, icon, color, created_at, updated_at
                FROM folders ORDER BY name
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            folders = []
            
            for row in cursor.fetchall():
                folder_data = dict(zip(columns, row))
                # Convert icon blob to base64 for easy handling in UI
                if folder_data['icon']:
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
            cursor = self.conn.cursor()
            update_fields = []
            params = []
            
            if name is not None:
                update_fields.append("name = ?")
                params.append(name)
            if icon_data is not None:
                update_fields.append("icon = ?")
                params.append(icon_data)
            if color is not None:
                update_fields.append("color = ?")
                params.append(color)
                
            update_fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(folder_id)
            
            if update_fields:
                query = f"UPDATE folders SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, params)
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
            cursor = self.conn.cursor()
            
            # Move passwords to another folder
            cursor.execute('''
                UPDATE passwords SET folder_id = ? WHERE folder_id = ?
            ''', (move_to_folder_id, folder_id))
            
            # Delete the folder
            cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
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
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO passwords (folder_id, title_encrypted, username_encrypted, 
                                    password_encrypted, url_encrypted, notes_encrypted)
                VALUES (?, ?, ?, ?, ?, ?)
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
            cursor = self.conn.cursor()
            if folder_id:
                cursor.execute('''
                    SELECT p.id, p.folder_id, p.title_encrypted, p.username_encrypted, 
                           p.password_encrypted, p.url_encrypted, p.notes_encrypted,
                           p.created_at, p.updated_at, f.name as folder_name
                    FROM passwords p
                    LEFT JOIN folders f ON p.folder_id = f.id
                    WHERE p.folder_id = ? 
                    ORDER BY p.title_encrypted
                ''', (folder_id,))
            else:
                cursor.execute('''
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
            cursor = self.conn.cursor()
            update_fields = []
            params = []
            
            if title is not None:
                update_fields.append("title_encrypted = ?")
                params.append(self.encrypt_data(title))
            if username is not None:
                update_fields.append("username_encrypted = ?")
                params.append(self.encrypt_data(username))
            if password is not None:
                update_fields.append("password_encrypted = ?")
                params.append(self.encrypt_data(password))
            if url is not None:
                update_fields.append("url_encrypted = ?")
                params.append(self.encrypt_data(url))
            if notes is not None:
                update_fields.append("notes_encrypted = ?")
                params.append(self.encrypt_data(notes))
            if folder_id is not None:
                update_fields.append("folder_id = ?")
                params.append(folder_id)
                
            update_fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(entry_id)
            
            if update_fields:
                query = f"UPDATE passwords SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, params)
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
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM passwords WHERE id = ?', (entry_id,))
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
            cursor = self.conn.cursor()
            cursor.execute('''
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