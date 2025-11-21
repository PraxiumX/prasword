# main_window.py
import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QListWidget, QStackedWidget,
                             QMessageBox, QToolBar, QStatusBar, QLabel, QPushButton,
                             QLineEdit, QTextEdit, QDialog, QDialogButtonBox,
                             QFormLayout, QGroupBox, QTabWidget, QMenu, QSystemTrayIcon,
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QTableWidget, QTableWidgetItem, QAbstractItemView, QInputDialog)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont, QKeySequence

# Add the missing imports
from database_manager import DatabaseManager
from add_password_dialog import AddPasswordDialog
from folder_manager_dialog import FolderManagerDialog
from database_dialog import DatabaseDialog
from settings_manager import SettingsManager

class PasswordTableWidget(QWidget):
    """KeePassXC-style table for displaying passwords"""
    password_selected = Signal(dict)
    password_activated = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()
        
    def setup_ui(self):
        # Search box with KeePassXC style
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search entries...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.on_search)
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_box)
        search_layout.addStretch()
        
        # Password table (KeePassXC uses a table view)
        self.password_table = QTableWidget()
        self.password_table.setColumnCount(4)
        self.password_table.setHorizontalHeaderLabels(["Title", "Username", "URL", "Folder"])
        self.password_table.horizontalHeader().setStretchLastSection(True)
        self.password_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.password_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.password_table.setAlternatingRowColors(True)
        self.password_table.setSortingEnabled(True)
        
        # Set column widths
        header = self.password_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Username
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # URL
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Folder
        
        self.password_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.password_table.doubleClicked.connect(self.on_double_click)
        
        self.layout.addLayout(search_layout)
        self.layout.addWidget(self.password_table)
        
    def load_passwords(self, passwords):
        self.password_table.setRowCount(0)
        print(f"Loading {len(passwords)} passwords")  # Debug
        
        for row, pwd in enumerate(passwords):
            if pwd and 'title' in pwd:  # Check if password data is valid and has title
                self.password_table.insertRow(row)
                
                # Title
                title_item = QTableWidgetItem(pwd['title'])
                title_item.setData(Qt.ItemDataRole.UserRole, pwd)
                self.password_table.setItem(row, 0, title_item)
                
                # Username
                username_item = QTableWidgetItem(pwd.get('username', '') or "")
                self.password_table.setItem(row, 1, username_item)
                
                # URL
                url_item = QTableWidgetItem(pwd.get('url', '') or "")
                self.password_table.setItem(row, 2, url_item)
                
                # Folder
                folder_item = QTableWidgetItem(pwd.get('folder_name', 'General'))
                self.password_table.setItem(row, 3, folder_item)
            
    def on_search(self, text):
        # Simple search implementation - hide rows that don't match
        for row in range(self.password_table.rowCount()):
            match = False
            for col in range(self.password_table.columnCount()):
                item = self.password_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.password_table.setRowHidden(row, not match)
        
    def on_selection_changed(self):
        selected_items = self.password_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            password_data = self.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if password_data:
                self.password_selected.emit(password_data)
                
    def on_double_click(self, index):
        row = index.row()
        password_data = self.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if password_data:
            self.password_activated.emit(password_data)

class PasswordDetailWidget(QWidget):
    """KeePassXC-style password details with tabs"""
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.current_password_data = None
        self.setup_ui()
        
    def setup_ui(self):
        # Title bar (like KeePassXC)
        title_layout = QHBoxLayout()
        self.title_label = QLabel("No entry selected")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border: 1px;
                border-radius: 4px;
            }
        """)
        title_layout.addWidget(self.title_label)
        
        # Tab widget for different detail sections (like KeePassXC)
        self.tab_widget = QTabWidget()
        
        # Entry tab (main details)
        self.entry_tab = QWidget()
        entry_layout = QFormLayout(self.entry_tab)
        
        self.username_value = QLabel()
        self.password_value = QLabel()
        self.password_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_value = QLabel()
        self.url_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_value.setOpenExternalLinks(False)
        self.notes_value = QTextEdit()
        self.notes_value.setReadOnly(True)
        self.notes_value.setMaximumHeight(150)
        
        entry_layout.addRow("Username:", self.username_value)
        entry_layout.addRow("Password:", self.password_value)
        entry_layout.addRow("URL:", self.url_value)
        entry_layout.addRow("Notes:", self.notes_value)
        
        # Advanced tab (additional info)
        self.advanced_tab = QWidget()
        advanced_layout = QFormLayout(self.advanced_tab)
        
        self.folder_value = QLabel()
        self.created_value = QLabel()
        self.modified_value = QLabel()
        
        advanced_layout.addRow("Folder:", self.folder_value)
        advanced_layout.addRow("Created:", self.created_value)
        advanced_layout.addRow("Modified:", self.modified_value)
        
        self.tab_widget.addTab(self.entry_tab, "Entry")
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        # Action buttons (KeePassXC style)
        button_layout = QHBoxLayout()
        
        self.copy_username_btn = QPushButton("Copy Username")
        self.copy_password_btn = QPushButton("Copy Password")
        self.copy_url_btn = QPushButton("Copy URL")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        
        self.copy_username_btn.clicked.connect(self.copy_username)
        self.copy_password_btn.clicked.connect(self.copy_password)
        self.copy_url_btn.clicked.connect(self.copy_url)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        
        button_layout.addWidget(self.copy_username_btn)
        button_layout.addWidget(self.copy_password_btn)
        button_layout.addWidget(self.copy_url_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        
        self.layout.addLayout(title_layout)
        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(button_layout)
        
        # Initially disable buttons
        self.set_buttons_enabled(False)
        
    def set_buttons_enabled(self, enabled):
        self.copy_username_btn.setEnabled(enabled)
        self.copy_password_btn.setEnabled(enabled)
        self.copy_url_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        
    def display_password(self, password_data):
        if not password_data:
            self.clear_display()
            return
            
        try:
            self.current_password_data = password_data
            self.title_label.setText(password_data.get('title', 'Unknown'))
            self.username_value.setText(password_data.get('username', '') or "N/A")
            self.password_value.setText("•" * 10)  # Masked password
            self.url_value.setText(password_data.get('url', '') or "N/A")
            self.notes_value.setText(password_data.get('notes', '') or "")
            self.folder_value.setText(password_data.get('folder_name', 'General'))
            
            # Format dates - handle both string and datetime objects
            created = password_data.get('created_at', '')
            modified = password_data.get('updated_at', '')
            
            if hasattr(created, 'strftime'):  # It's a datetime object
                self.created_value.setText(created.strftime("%Y-%m-%d %H:%M:%S"))
            else:  # It's a string
                self.created_value.setText(str(created)[:19] if created else "N/A")
                
            if hasattr(modified, 'strftime'):  # It's a datetime object
                self.modified_value.setText(modified.strftime("%Y-%m-%d %H:%M:%S"))
            else:  # It's a string
                self.modified_value.setText(str(modified)[:19] if modified else "N/A")
            
            self.set_buttons_enabled(True)
            
        except Exception as e:
            print(f"Error displaying password: {e}")
            self.clear_display()
        
    def clear_display(self):
        self.title_label.setText("No entry selected")
        self.username_value.setText("")
        self.password_value.setText("")
        self.url_value.setText("")
        self.notes_value.setText("")
        self.folder_value.setText("")
        self.created_value.setText("")
        self.modified_value.setText("")
        self.current_password_data = None
        self.set_buttons_enabled(False)
        
    def copy_username(self):
        if self.current_password_data and self.current_password_data.get('username'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_password_data['username'])
            QMessageBox.information(self, "Copied", "Username copied to clipboard!")
            
    def copy_password(self):
        if self.current_password_data and self.current_password_data.get('password'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_password_data['password'])
            QMessageBox.information(self, "Copied", "Password copied to clipboard!")
            
    def copy_url(self):
        if self.current_password_data and self.current_password_data.get('url'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_password_data['url'])
            QMessageBox.information(self, "Copied", "URL copied to clipboard!")
            
    def on_edit_clicked(self):
        if self.current_password_data:
            self.edit_requested.emit(self.current_password_data)
            
    def on_delete_clicked(self):
        if self.current_password_data:
            self.delete_requested.emit(self.current_password_data)

class FoldersTreeWidget(QWidget):
    """KeePassXC-style tree view for folders"""
    folder_selected = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()
        
    def setup_ui(self):
        # Tree widget for folders (like KeePassXC)
        self.folders_tree = QTreeWidget()
        self.folders_tree.setHeaderLabel("Groups")
        self.folders_tree.itemSelectionChanged.connect(self.on_folder_selected)
        
        # Add folder button
        self.add_folder_btn = QPushButton("Add Group")
        self.manage_folders_btn = QPushButton("Manage Groups")
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_folder_btn)
        button_layout.addWidget(self.manage_folders_btn)
        
        self.layout.addWidget(QLabel("Groups:"))
        self.layout.addWidget(self.folders_tree)
        self.layout.addLayout(button_layout)
        
    def load_folders(self, folders):
        self.folders_tree.clear()
        print(f"Loading {len(folders)} folders")  # Debug
        
        # Create root item
        root_item = QTreeWidgetItem(self.folders_tree, ["Database"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, 0)  # 0 for root
        
        for folder in folders:
            if folder and 'id' in folder:  # Check if folder data is valid
                item_text = f"{folder['name']} ({folder.get('password_count', 0)})"
                item = QTreeWidgetItem(root_item, [item_text])
                item.setData(0, Qt.ItemDataRole.UserRole, folder['id'])
                
        self.folders_tree.expandAll()

    def on_folder_selected(self):
        selected_items = self.folders_tree.selectedItems()
        if selected_items:
            folder_id = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if folder_id is not None and folder_id != 0:  # Check if folder_id is valid and not root
                print(f"Folder selected: {folder_id}")  # Debug
                self.folder_selected.emit(folder_id)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.settings_manager = SettingsManager()
        self.current_folder_id = 1
        self.current_database = None
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        
    def setup_ui(self):
        self.setWindowTitle("prasword - No Database")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left sidebar - Folders tree (like KeePassXC)
        self.folders_widget = FoldersTreeWidget()
        self.folders_widget.folder_selected.connect(self.on_folder_selected)
        self.folders_widget.add_folder_btn.clicked.connect(self.add_folder_quick)
        self.folders_widget.manage_folders_btn.clicked.connect(self.manage_folders)
        
        # Right side - Splitter for password table and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Password table (top)
        self.password_table_widget = PasswordTableWidget()
        self.password_table_widget.password_selected.connect(self.on_password_selected)
        self.password_table_widget.password_activated.connect(self.on_password_activated)
        
        # Password details (bottom)
        self.password_detail_widget = PasswordDetailWidget()
        self.password_detail_widget.edit_requested.connect(self.edit_password)
        self.password_detail_widget.delete_requested.connect(self.delete_password)
        
        splitter.addWidget(self.password_table_widget)
        splitter.addWidget(self.password_detail_widget)
        splitter.setSizes([400, 300])
        
        # Main layout
        main_layout.addWidget(self.folders_widget, 1)
        main_layout.addWidget(splitter, 3)
        
        # Status bar
        self.statusBar().showMessage("No database connected")
        
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_db_action = QAction("&New Database", self)
        new_db_action.setShortcut(QKeySequence.StandardKey.New)
        new_db_action.triggered.connect(self.show_database_dialog)
        file_menu.addAction(new_db_action)
        
        file_menu.addSeparator()
        
        lock_db_action = QAction("&Lock Database", self)
        lock_db_action.setShortcut("Ctrl+L")
        lock_db_action.triggered.connect(self.lock_database)
        file_menu.addAction(lock_db_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Entry menu
        entry_menu = menubar.addMenu("&Entry")
        
        add_entry_action = QAction("&Add Entry", self)
        add_entry_action.setShortcut(QKeySequence.StandardKey.New)
        add_entry_action.triggered.connect(self.add_password)
        entry_menu.addAction(add_entry_action)
        
        edit_entry_action = QAction("&Edit Entry", self)
        edit_entry_action.setShortcut("Ctrl+E")
        edit_entry_action.triggered.connect(self.edit_current_password)
        entry_menu.addAction(edit_entry_action)
        
        delete_entry_action = QAction("&Delete Entry", self)
        delete_entry_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_entry_action.triggered.connect(self.delete_current_password)
        entry_menu.addAction(delete_entry_action)
        
        entry_menu.addSeparator()
        
        copy_username_action = QAction("Copy &Username", self)
        copy_username_action.setShortcut("Ctrl+U")
        copy_username_action.triggered.connect(self.copy_username)
        entry_menu.addAction(copy_username_action)
        
        copy_password_action = QAction("Copy &Password", self)
        copy_password_action.setShortcut("Ctrl+P")
        copy_password_action.triggered.connect(self.copy_password)
        entry_menu.addAction(copy_password_action)
        
        copy_url_action = QAction("Copy &URL", self)
        copy_url_action.setShortcut("Ctrl+R")
        copy_url_action.triggered.connect(self.copy_url)
        entry_menu.addAction(copy_url_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        toggle_details_action = QAction("&Show Details", self)
        toggle_details_action.setCheckable(True)
        toggle_details_action.setChecked(True)
        toggle_details_action.triggered.connect(self.toggle_details)
        view_menu.addAction(toggle_details_action)
        
    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Database actions
        new_db_action = QAction("New DB", self)
        new_db_action.triggered.connect(self.show_database_dialog)
        toolbar.addAction(new_db_action)
        
        toolbar.addSeparator()
        
        # Password actions
        add_entry_action = QAction("Add Entry", self)
        add_entry_action.triggered.connect(self.add_password)
        toolbar.addAction(add_entry_action)
        
    def show_database_dialog(self):
        """Show database creation/management dialog"""
        dialog = DatabaseDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            db_config = dialog.get_selected_database()
            if db_config:
                self.connect_to_database(db_config)
    
    def connect_to_database(self, db_config):
        """Connect to selected database"""
        try:
            print(f"Connecting to database: {db_config['name']} ({db_config['type']})")
            
            success = False
            if db_config['type'] == 'sqlite':
                success = self.db_manager.connect_sqlite_database(
                    db_config['path'], 
                    db_config['master_password']
                )
            else:  # postgresql
                success = self.db_manager.connect_postgresql_database(
                    db_config['config'],
                    db_config['master_password']
                )
                
            if success:
                self.current_database = db_config
                self.set_database_connected(True)
                self.setWindowTitle(f"prasword - {db_config['name']} ({db_config['type']})")
                self.statusBar().showMessage(f"Connected to {db_config['name']}")
                print("Database connected successfully")
                
                # Test if we can actually read data
                test_folders = self.db_manager.get_folders()
                print(f"Test: Retrieved {len(test_folders)} folders")
                
            else:
                self.set_database_connected(False)
                QMessageBox.warning(self, "Error", f"Failed to connect to {db_config['name']}. Check master password.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database connection error: {str(e)}")
    
    def lock_database(self):
        if self.db_manager.is_connected:
            self.db_manager.close()
            self.set_database_connected(False)
            self.setWindowTitle("prasword - Locked")
            QMessageBox.information(self, "Database Locked", "Database has been locked. Use 'Database' menu to reconnect.")
        else:
            QMessageBox.information(self, "Info", "No database is currently connected.")
        
    def add_password(self):
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected. Cannot add password.")
            return
            
        dialog = AddPasswordDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_passwords()
            QMessageBox.information(self, "Success", "Password added successfully!")
    
    def edit_current_password(self):
        """Edit currently selected password"""
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected.")
            return
            
        if hasattr(self.password_detail_widget, 'current_password_data') and self.password_detail_widget.current_password_data:
            self.edit_password(self.password_detail_widget.current_password_data)
        else:
            QMessageBox.warning(self, "Error", "No password selected to edit.")
    
    def edit_password(self, password_data=None):
        """Edit existing password entry"""
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected.")
            return
            
        if not password_data:
            selected_items = self.password_table_widget.password_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Error", "No password selected to edit.")
                return
            row = selected_items[0].row()
            password_data = self.password_table_widget.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if password_data and 'id' in password_data:
            dialog = AddPasswordDialog(self.db_manager, self, password_data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_passwords()
                QMessageBox.information(self, "Success", "Password updated successfully!")
        else:
            QMessageBox.warning(self, "Error", "No valid password data available to edit.")
    
    def delete_current_password(self):
        """Delete currently selected password"""
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected.")
            return
            
        if hasattr(self.password_detail_widget, 'current_password_data') and self.password_detail_widget.current_password_data:
            self.delete_password(self.password_detail_widget.current_password_data)
        else:
            QMessageBox.warning(self, "Error", "No password selected to delete.")
        
    def delete_password(self, password_data=None):
        """Delete password entry"""
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected.")
            return
            
        if not password_data:
            selected_items = self.password_table_widget.password_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Error", "No password selected to delete.")
                return
            row = selected_items[0].row()
            password_data = self.password_table_widget.password_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if password_data and 'id' in password_data:
            reply = QMessageBox.question(
                self, 
                "Confirm Delete", 
                f"Are you sure you want to delete '{password_data.get('title', 'Unknown')}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.db_manager.delete_password(password_data['id'])
                if success:
                    self.refresh_passwords()
                    self.password_detail_widget.display_password(None)
                    QMessageBox.information(self, "Success", "Password deleted successfully!")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete password.")
        else:
            QMessageBox.warning(self, "Error", "No valid password data available to delete.")
        
    def copy_username(self):
        if hasattr(self.password_detail_widget, 'current_password_data') and self.password_detail_widget.current_password_data:
            self.password_detail_widget.copy_username()
        else:
            QMessageBox.warning(self, "Error", "No password selected.")
        
    def copy_password(self):
        if hasattr(self.password_detail_widget, 'current_password_data') and self.password_detail_widget.current_password_data:
            self.password_detail_widget.copy_password()
        else:
            QMessageBox.warning(self, "Error", "No password selected.")
    
    def copy_url(self):
        if hasattr(self.password_detail_widget, 'current_password_data') and self.password_detail_widget.current_password_data:
            self.password_detail_widget.copy_url()
        else:
            QMessageBox.warning(self, "Error", "No password selected.")
            
    def toggle_details(self, checked):
        if hasattr(self, 'password_detail_widget'):
            self.password_detail_widget.setVisible(checked)
        
    def add_folder_quick(self):
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected. Cannot add folder.")
            return
            
        name, ok = QInputDialog.getText(self, "Add Group", "Group name:")
        if ok and name:
            # Fix for PostgreSQL "no results to fetch" error
            folder_id = self.db_manager.create_folder(name)
            if folder_id != -1:
                self.refresh_folders()
                QMessageBox.information(self, "Success", f"Group '{name}' created!")
            else:
                QMessageBox.warning(self, "Error", "Failed to create group")
        
    def manage_folders(self):
        if not self.db_manager.is_connected:
            QMessageBox.warning(self, "Error", "Database not connected. Cannot manage folders.")
            return
            
        dialog = FolderManagerDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_folders()
            self.refresh_passwords()
            QMessageBox.information(self, "Success", "Groups updated successfully!")
        
    def on_folder_selected(self, folder_id):
        if folder_id is not None:
            self.current_folder_id = folder_id
            print(f"Current folder set to: {folder_id}")
            self.refresh_passwords()
        
    def on_password_selected(self, password_data):
        if password_data:
            print(f"Password selected: {password_data.get('title', 'Unknown')}")
            self.password_detail_widget.display_password(password_data)
            
    def on_password_activated(self, password_data):
        if password_data and password_data.get('password'):
            clipboard = QApplication.clipboard()
            clipboard.setText(password_data['password'])
            QMessageBox.information(self, "Copied", "Password copied to clipboard!")
        
    def refresh_folders(self):
        if not self.db_manager.is_connected:
            return
            
        folders = self.db_manager.get_folders()
        print(f"Retrieved {len(folders)} folders")
        password_counts = self.db_manager.get_password_count_by_folder()
        
        for folder in folders:
            if folder:
                folder['password_count'] = next(
                    (pc['password_count'] for pc in password_counts if pc['id'] == folder['id']), 0
                )
            
        self.folders_widget.load_folders(folders)
        
    def refresh_passwords(self):
        if not self.db_manager.is_connected:
            return
            
        print(f"Refreshing passwords for folder: {self.current_folder_id}")
        passwords = self.db_manager.get_passwords(self.current_folder_id)
        print(f"Retrieved {len(passwords)} passwords")
        
        # Check if passwords are properly decrypted
        for pwd in passwords:
            if pwd and 'title' not in pwd:
                print(f"Warning: Password missing title: {pwd}")
        
        self.password_table_widget.load_passwords(passwords)
        
    def set_database_connected(self, connected):
        if connected:
            self.refresh_folders()
            self.refresh_passwords()
            self.statusBar().showMessage("Database connected")
        else:
            self.folders_widget.load_folders([])
            self.password_table_widget.load_passwords([])
            self.password_detail_widget.display_password(None)
            self.statusBar().showMessage("No database connected")