# Create README.md
cat > README.md << 'EOF'
# Prasword - Password Manager

A secure, local password manager built with Python and PySide6, featuring KeePassXC-like interface with encrypted database storage.

## Features

- 🔐 **AES-256 Encryption** using cryptography library
- 🗂️ **Folder/Group Organization** with tree view
- 🔍 **Search Functionality** across all entries
- 📋 **Copy to Clipboard** for usernames, passwords, and URLs
- 🎨 **KeePassXC-inspired Interface** with modern UI
- 🔄 **Add/Edit/Delete** password entries
- 📁 **Database Encryption** with master password
- 🛡️ **Local Storage** - your data never leaves your computer

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/praxiumx/prasword.git
   cd prasword