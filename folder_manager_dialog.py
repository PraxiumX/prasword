# folder_manager_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QLineEdit, QPushButton, QDialogButtonBox, QColorDialog,
                             QLabel, QMessageBox, QListWidgetItem, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from icon_utils import pixmap_to_bytes

class FolderManagerDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_folder_id = None
        self.setup_ui()
        self.load_folders()
        
    def setup_ui(self):
        self.setWindowTitle("Manage Folders")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QHBoxLayout(self)
        
        # Left side - Folder list
        left_layout = QVBoxLayout()
        
        self.folders_list = QListWidget()
        self.folders_list.itemSelectionChanged.connect(self.on_folder_selected)
        
        left_layout.addWidget(QLabel("Folders:"))
        left_layout.addWidget(self.folders_list)
        
        # Right side - Folder details
        right_layout = QVBoxLayout()
        
        # Folder name
        right_layout.addWidget(QLabel("Folder Name:"))
        self.name_input = QLineEdit()
        right_layout.addWidget(self.name_input)
        
        # Icon selection
        right_layout.addWidget(QLabel("Folder Icon:"))
        icon_layout = QHBoxLayout()
        self.icon_btn = QPushButton("Select Icon")
        self.icon_btn.clicked.connect(self.select_icon)
        self.clear_icon_btn = QPushButton("Clear Icon")
        self.clear_icon_btn.clicked.connect(self.clear_icon)
        
        icon_layout.addWidget(self.icon_btn)
        icon_layout.addWidget(self.clear_icon_btn)
        icon_layout.addStretch()
        
        right_layout.addLayout(icon_layout)
        
        # Color selection
        right_layout.addWidget(QLabel("Folder Color:"))
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("Select Color")
        self.color_btn.clicked.connect(self.select_color)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet("background-color: #3498db; border: 1px solid #ccc;")
        
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        
        right_layout.addLayout(color_layout)
        right_layout.addStretch()
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Folder")
        self.add_btn.clicked.connect(self.add_folder)
        self.update_btn = QPushButton("Update Folder")
        self.update_btn.clicked.connect(self.update_folder)
        self.delete_btn = QPushButton("Delete Folder")
        self.delete_btn.clicked.connect(self.delete_folder)
        
        action_layout.addWidget(self.add_btn)
        action_layout.addWidget(self.update_btn)
        action_layout.addWidget(self.delete_btn)
        
        right_layout.addLayout(action_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        right_layout.addWidget(button_box)
        
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 1)
        
        self.selected_icon_data = None
        self.selected_color = "#3498db"
        
    def load_folders(self):
        self.folders_list.clear()
        folders = self.db_manager.get_folders()
        print(f"Loading {len(folders)} folders in dialog")  # Debug
        for folder in folders:
            if folder:  # Check if folder data is valid
                item = QListWidgetItem(folder['name'])
                item.setData(Qt.ItemDataRole.UserRole, folder)
                self.folders_list.addItem(item)
            
    def on_folder_selected(self):
        selected_items = self.folders_list.selectedItems()
        if selected_items:
            folder_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if folder_data:  # Check if folder_data is valid
                self.current_folder_id = folder_data['id']
                self.name_input.setText(folder_data['name'])
                self.selected_color = folder_data.get('color', '#3498db')
                self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
                
                # Load icon if exists
                if folder_data.get('icon'):
                    self.selected_icon_data = folder_data['icon']
                else:
                    self.selected_icon_data = None
                
    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Folder Icon", 
            "", 
            "Images (*.png *.jpg *.jpeg *.ico *.svg)"
        )
        
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                self.selected_icon_data = pixmap_to_bytes(pixmap)
                
    def clear_icon(self):
        self.selected_icon_data = None
        
    def select_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
            
    def add_folder(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Folder name cannot be empty")
            return
            
        folder_id = self.db_manager.create_folder(name, self.selected_icon_data, self.selected_color)
        if folder_id != -1:
            self.load_folders()  # Reload the folder list
            self.clear_form()
            QMessageBox.information(self, "Success", f"Folder '{name}' created successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to create folder")
            
    def update_folder(self):
        if not self.current_folder_id:
            QMessageBox.warning(self, "Error", "No folder selected")
            return
            
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Folder name cannot be empty")
            return
            
        success = self.db_manager.update_folder(
            self.current_folder_id, 
            name, 
            self.selected_icon_data, 
            self.selected_color
        )
        
        if success:
            self.load_folders()  # Reload the folder list
            QMessageBox.information(self, "Success", f"Folder updated successfully!")
        else:
            QMessageBox.warning(self, "Error", "Failed to update folder")
            
    def delete_folder(self):
        if not self.current_folder_id or self.current_folder_id == 1:
            QMessageBox.warning(self, "Error", "Cannot delete the default folder")
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            "Are you sure you want to delete this folder? All passwords will be moved to the General folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.db_manager.delete_folder(self.current_folder_id)
            if success:
                self.load_folders()  # Reload the folder list
                self.clear_form()
                QMessageBox.information(self, "Success", "Folder deleted successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete folder")
                
    def clear_form(self):
        self.current_folder_id = None
        self.name_input.clear()
        self.selected_icon_data = None
        self.selected_color = "#3498db"
        self.color_preview.setStyleSheet("background-color: #3498db; border: 1px solid #ccc;")
        self.folders_list.clearSelection()