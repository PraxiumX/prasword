# Prasword - Password Manager

A secure, local or self-hosted postgresql password manager built with Python and PySide6, featuring KeePassXC-like interface with encrypted database storage.

## Features

- 🔐 **AES-256 Encryption** using cryptography library
- 🗂️ **Folder/Group Organization** with tree view
- 🔍 **Search Functionality** across all entries
- 📋 **Copy to Clipboard** for usernames, passwords, and URLs
- 🎨 **KeePassXC-inspired Interface** with modern UI
- 🔄 **Add/Edit/Delete** password entries
- 📁 **Database Encryption** with master password
- 🛡️ **Local Storage** - your data never leaves your computer
- 💾 **Multiple Database Support** - SQLite and PostgreSQL
- 🔒 **Auto-lock** functionality
- 📱 **Cross-platform** - Windows, macOS, Linux

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/praxiumx/prasword.git
   cd prasword

# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python main.py

# Quick start

-**Windows**
start.bat

-**Linux**
chmod +x start.sh
./start.sh
