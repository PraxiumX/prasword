# add_password_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QTextEdit, QComboBox, QPushButton, 
                             QDialogButtonBox, QGroupBox, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt

class AddPasswordDialog(QDialog):
    def __init__(self, db_manager, parent=None, password_data=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.password_data = password_data  # Store password data for edit mode
        self.setup_ui()
        self.load_folders()
        self.load_existing_data()  # Load existing data if editing
        
    def setup_ui(self):
        # Set title based on mode
        title = "Edit Password" if self.password_data else "Add New Password"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Form group
        form_group = QGroupBox("Password Details")
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Show password checkbox
        self.show_password_checkbox = QCheckBox("Show Password")
        self.show_password_checkbox.toggled.connect(self.toggle_password_visibility)
        
        self.url_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.folder_combo = QComboBox()
        
        form_layout.addRow("Title*:", self.title_input)
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password*:", self.password_input)
        form_layout.addRow("", self.show_password_checkbox)  # Empty label for alignment
        form_layout.addRow("URL:", self.url_input)
        form_layout.addRow("Folder:", self.folder_combo)
        form_layout.addRow("Notes:", self.notes_input)
        
        form_group.setLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Generate password button
        generate_btn = QPushButton("Generate Password")
        generate_btn.clicked.connect(self.generate_password)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(generate_btn)
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        
        layout.addWidget(form_group)
        layout.addLayout(button_layout)
        
    def load_folders(self):
        folders = self.db_manager.get_folders()
        for folder in folders:
            self.folder_combo.addItem(folder['name'], folder['id'])
            
    def load_existing_data(self):
        """Load existing data when in edit mode"""
        if self.password_data:
            self.title_input.setText(self.password_data.get('title', ''))
            self.username_input.setText(self.password_data.get('username', ''))
            self.password_input.setText(self.password_data.get('password', ''))
            self.url_input.setText(self.password_data.get('url', ''))
            self.notes_input.setPlainText(self.password_data.get('notes', ''))
            
            # Set the folder in combo box
            folder_id = self.password_data.get('folder_id', 1)
            index = self.folder_combo.findData(folder_id)
            if index >= 0:
                self.folder_combo.setCurrentIndex(index)
            
    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            
    def generate_password(self):
        # Simple password generator
        import random
        import string
        length = 16
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(characters) for i in range(length))
        self.password_input.setText(password)
        
    def accept(self):
        # Validate inputs
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Error", "Title is required")
            return
            
        if not self.password_input.text().strip():
            QMessageBox.warning(self, "Error", "Password is required")
            return
            
        # Get folder ID
        folder_id = self.folder_combo.currentData()
        if not folder_id:
            folder_id = 1  # Default folder
            
        if self.password_data:
            # Update existing password
            success = self.db_manager.update_password(
                entry_id=self.password_data['id'],
                title=self.title_input.text().strip(),
                username=self.username_input.text().strip(),
                password=self.password_input.text(),
                url=self.url_input.text().strip(),
                notes=self.notes_input.toPlainText().strip(),
                folder_id=folder_id
            )
        else:
            # Add new password
            success = self.db_manager.add_password(
                title=self.title_input.text().strip(),
                username=self.username_input.text().strip(),
                password=self.password_input.text(),
                folder_id=folder_id,
                url=self.url_input.text().strip(),
                notes=self.notes_input.toPlainText().strip()
            )
        
        if success:
            super().accept()
        else:
            QMessageBox.warning(self, "Error", "Failed to save password to database")