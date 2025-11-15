import sys, os

def resource_path(relative_path):
    """หาไฟล์ให้ถูกทั้งตอนรันจาก .py และ .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)