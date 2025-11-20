# icon_utils.py
import base64
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QBuffer, QByteArray, QIODevice

def pixmap_to_bytes(pixmap: QPixmap) -> bytes:
    """Convert QPixmap to bytes for storage"""
    if pixmap.isNull():
        return None
        
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    return byte_array.data()

def bytes_to_pixmap(icon_data: bytes) -> QPixmap:
    """Convert stored bytes back to QPixmap"""
    if not icon_data:
        return QPixmap()
        
    pixmap = QPixmap()
    pixmap.loadFromData(icon_data)
    return pixmap

def bytes_to_base64(icon_data: bytes) -> str:
    """Convert icon bytes to base64 string for easy handling"""
    if not icon_data:
        return ""
    return base64.b64encode(icon_data).decode('utf-8')

def base64_to_bytes(base64_str: str) -> bytes:
    """Convert base64 string back to bytes"""
    if not base64_str:
        return None
    return base64.b64decode(base64_str)