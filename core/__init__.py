import sys
import os

def get_launcher_root():
    """
    Hàm này giúp Launcher luôn tìm đúng thư mục gốc,
    bất kể là đang chạy bằng file .py hay file .exe.
    """
    if getattr(sys, 'frozen', False):
        # Nếu đang chạy bằng file .exe đã build
        return os.path.dirname(sys.executable)
    else:
        # Nếu đang chạy bằng file code .py
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))