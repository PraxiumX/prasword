# database_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QComboBox, QPushButton, QDialogButtonBox,
                             QGroupBox, QMessageBox, QTabWidget, QWidget, QLabel,
                             QSpinBox, QListWidget, QListWidgetItem, QInputDialog)
from PySide6.QtCore import Qt
from database_manager import DatabaseManager
from settings_manager import SettingsManager

class DatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.selected_database = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Manage Databases")
        self.setModal(True)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Tab widget for different database types
        self.tab_widget = QTabWidget()
        
        # Local Databases Tab
        self.local_tab = QWidget()
        self.setup_local_tab()
        
        # PostgreSQL Tab
        self.postgresql_tab = QWidget()
        self.setup_postgresql_tab()
        
        # Existing Databases Tab (Integrated Connection Dialog)
        self.existing_tab = QWidget()
        self.setup_existing_tab()
        
        self.tab_widget.addTab(self.local_tab, "Local Database")
        self.tab_widget.addTab(self.postgresql_tab, "PostgreSQL")
        self.tab_widget.addTab(self.existing_tab, "Connect to Database")
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
    def setup_local_tab(self):
        layout = QVBoxLayout(self.local_tab)
        
        form_group = QGroupBox("Create New Local Database")
        form_layout = QFormLayout()
        
        self.local_name_input = QLineEdit()
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText("e.g., my_passwords.db")
        self.local_master_input = QLineEdit()
        self.local_master_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_local_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.local_path_input)
        path_layout.addWidget(browse_btn)
        
        form_layout.addRow("Database Name:", self.local_name_input)
        form_layout.addRow("File Path:", path_layout)
        form_layout.addRow("Master Password:", self.local_master_input)
        
        create_btn = QPushButton("Create Database")
        create_btn.clicked.connect(self.create_local_database)
        
        form_group.setLayout(form_layout)
        
        layout.addWidget(form_group)
        layout.addWidget(create_btn)
        layout.addStretch()
        
    def setup_postgresql_tab(self):
        layout = QVBoxLayout(self.postgresql_tab)
        
        form_group = QGroupBox("PostgreSQL Connection")
        form_layout = QFormLayout()
        
        self.pg_name_input = QLineEdit()
        self.pg_host_input = QLineEdit()
        self.pg_host_input.setText("localhost")
        self.pg_port_input = QSpinBox()
        self.pg_port_input.setRange(1, 65535)
        self.pg_port_input.setValue(5432)
        self.pg_db_input = QLineEdit()
        self.pg_user_input = QLineEdit()
        self.pg_password_input = QLineEdit()
        self.pg_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pg_master_input = QLineEdit()
        self.pg_master_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("Connection Name:", self.pg_name_input)
        form_layout.addRow("Host:", self.pg_host_input)
        form_layout.addRow("Port:", self.pg_port_input)
        form_layout.addRow("Database Name:", self.pg_db_input)
        form_layout.addRow("Username:", self.pg_user_input)
        form_layout.addRow("Password:", self.pg_password_input)
        form_layout.addRow("Master Password:", self.pg_master_input)
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_postgresql_connection)
        
        create_btn = QPushButton("Create/Save Database")
        create_btn.clicked.connect(self.create_postgresql_database)
        
        form_group.setLayout(form_layout)
        
        layout.addWidget(form_group)
        layout.addWidget(test_btn)
        layout.addWidget(create_btn)
        layout.addStretch()
        
    def setup_existing_tab(self):
        layout = QVBoxLayout(self.existing_tab)
        
        # Master password input for viewing saved databases
        master_layout = QHBoxLayout()
        self.master_password_input = QLineEdit()
        self.master_password_input.setPlaceholderText("Enter master password to view databases")
        self.master_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        load_btn = QPushButton("Load Databases")
        load_btn.clicked.connect(self.load_existing_databases)
        
        master_layout.addWidget(QLabel("Master Password:"))
        master_layout.addWidget(self.master_password_input)
        master_layout.addWidget(load_btn)
        
        # Database list
        layout.addLayout(master_layout)
        layout.addWidget(QLabel("Saved Databases:"))
        
        self.existing_list = QListWidget()
        self.existing_list.itemDoubleClicked.connect(self.connect_to_database)
        layout.addWidget(self.existing_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_database)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.remove_database)
        
        buttons_layout.addWidget(self.connect_btn)
        buttons_layout.addWidget(self.remove_btn)
        
        layout.addLayout(buttons_layout)
        
    def browse_local_path(self):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Database Location", "", "Database Files (*.db)"
        )
        if file_path:
            self.local_path_input.setText(file_path)
            
    def create_local_database(self):
        name = self.local_name_input.text().strip()
        path = self.local_path_input.text().strip()
        master_password = self.local_master_input.text().strip()
        
        if not name or not path or not master_password:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        db_manager = DatabaseManager()
        success = db_manager.create_sqlite_database(path, master_password)
        
        if success:
            # Save to settings
            db_config = {
                'name': name,
                'type': 'sqlite',
                'path': path,
                'master_password': master_password
            }
            
            if self.settings_manager.add_database(db_config, master_password):
                QMessageBox.information(self, "Success", "Local database created and saved!")
                self.load_existing_databases()
                self.local_name_input.clear()
                self.local_path_input.clear()
                self.local_master_input.clear()
            else:
                QMessageBox.warning(self, "Error", "Failed to save database configuration")
        else:
            QMessageBox.warning(self, "Error", "Failed to create database")
            
    def test_postgresql_connection(self):
        # Test PostgreSQL connection without creating database
        host = self.pg_host_input.text().strip()
        port = self.pg_port_input.value()
        database = self.pg_db_input.text().strip()
        user = self.pg_user_input.text().strip()
        password = self.pg_password_input.text().strip()
        
        if not all([host, database, user, password]):
            QMessageBox.warning(self, "Error", "Please fill all PostgreSQL connection fields")
            return
            
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            conn.close()
            QMessageBox.information(self, "Success", "PostgreSQL connection successful!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"PostgreSQL connection failed: {str(e)}")
            
    def create_postgresql_database(self):
        name = self.pg_name_input.text().strip()
        host = self.pg_host_input.text().strip()
        port = self.pg_port_input.value()
        database = self.pg_db_input.text().strip()
        user = self.pg_user_input.text().strip()
        password = self.pg_password_input.text().strip()
        master_password = self.pg_master_input.text().strip()
        
        if not all([name, host, database, user, password, master_password]):
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return
            
        db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        db_manager = DatabaseManager()
        success = db_manager.create_postgresql_database(db_config, master_password)
        
        if success:
            # Save to settings
            full_config = {
                'name': name,
                'type': 'postgresql',
                'config': db_config,
                'master_password': master_password
            }
            
            if self.settings_manager.add_database(full_config, master_password):
                QMessageBox.information(self, "Success", "PostgreSQL database created and saved!")
                self.load_existing_databases()
                self.pg_name_input.clear()
                self.pg_host_input.clear()
                self.pg_db_input.clear()
                self.pg_user_input.clear()
                self.pg_password_input.clear()
                self.pg_master_input.clear()
            else:
                QMessageBox.warning(self, "Error", "Failed to save database configuration")
        else:
            QMessageBox.warning(self, "Error", "Failed to create PostgreSQL database")
            
    def load_existing_databases(self):
        master_password = self.master_password_input.text().strip()
        self.existing_list.clear()
        
        if not master_password:
            QMessageBox.warning(self, "Error", "Please enter master password")
            return
            
        databases = self.settings_manager.load_database_settings(master_password)
        if databases is None:
            QMessageBox.warning(self, "Error", "Invalid master password or corrupted settings file")
            return
            
        for db in databases:
            item_text = f"{db['name']} ({db['type']})"
            if db['type'] == 'sqlite':
                # Show obscured path
                path = db['path']
                if len(path) > 30:
                    path = "..." + path[-27:]
                item_text += f" - {path}"
            else:
                # Show obscured connection details
                host = db['config']['host']
                database = db['config']['database']
                item_text += f" - {host}/••••••"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, db)
            self.existing_list.addItem(item)
            
    def connect_to_database(self):
        current_item = self.existing_list.currentItem()
        master_password = self.master_password_input.text().strip()
        
        if not current_item or not master_password:
            QMessageBox.warning(self, "Error", "Please select a database and enter master password")
            return
            
        db_config = current_item.data(Qt.ItemDataRole.UserRole)
        # Add master password to the config for the main window to use
        db_config['master_password'] = master_password
        self.selected_database = db_config
        self.accept()
        
    def remove_database(self):
        current_item = self.existing_list.currentItem()
        master_password = self.master_password_input.text().strip()
        
        if not current_item or not master_password:
            QMessageBox.warning(self, "Error", "Please select a database to remove")
            return
            
        db_config = current_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, 
            "Confirm Remove", 
            f"Are you sure you want to remove database '{db_config['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.settings_manager.remove_database(db_config['name'], master_password):
                self.load_existing_databases()
                QMessageBox.information(self, "Success", "Database removed successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to remove database")
    
    def get_selected_database(self):
        return self.selected_database