#main.py
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from ui.login import LoginWindow
from ui.main_window import MainWindow
# Bổ sung import hàm xử lý kiểm tra đăng nhập tự động
from core.auth import get_current_session
# IMPORT HÀM ĐỒNG BỘ VỪA VIẾT
from core.network import sync_and_fetch_games

# ====================================================================
# FIX LỖI HIỂN THỊ ICON TỜ GIẤY TRẮNG DƯỚI TASKBAR CỦA WINDOWS
# ====================================================================
if sys.platform == "win32":
    import ctypes
    # Định danh ID ứng dụng để Windows biết đây là app độc lập
    myappid = "vangrok.launcher.game.v1.0" 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass # Bỏ qua nếu Windows quá cũ không hỗ trợ hàm này

def main():
    app = QApplication(sys.argv)
    
    # Xác định đường dẫn gốc
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # ====================================================================
    # [MỚI] ĐỒNG BỘ GAME & DỌN DẸP ẢNH RÁC NGAY KHI KHỞI ĐỘNG
    # ====================================================================
    print("⏳ Đang đồng bộ dữ liệu với máy chủ Vangrok...")
    sync_and_fetch_games(base_dir)
    
    # ====================================================================
    # THIẾT LẬP ICON CHO TOÀN BỘ ỨNG DỤNG (TASKBAR & GÓC CỬA SỔ)
    # ====================================================================
    icon_path = os.path.join(base_dir, "assets", "logo.ico")
    
    # Cố gắng tìm icon ở thư mục gốc, nếu không thấy sẽ tìm trong _internal (khi build)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        internal_icon_path = os.path.join(base_dir, "_internal", "assets", "logo.ico")
        if os.path.exists(internal_icon_path):
            app.setWindowIcon(QIcon(internal_icon_path))
            
    # 1. Kiểm tra session ngay khi khởi động
    session = get_current_session()
    auto_login = False
    
    # Khai báo sẵn các biến chứa thông tin user
    current_username = ""
    current_is_admin = False
    current_is_verified = False  # [MỚI] Khởi tạo trạng thái xác thực ban đầu
    
    if session:
        auto_login = True
        current_username = session.get("username")
        current_is_admin = session.get("is_admin", False)
        current_is_verified = session.get("is_verified", False)  # [MỚI] Đọc từ session cũ nếu có
    
    # Vòng lặp quản lý luồng sống của ứng dụng
    while True:
        if auto_login:
            # Nếu có session, bỏ qua màn hình Đăng nhập ở lần chạy đầu tiên
            auto_login = False  # Reset cờ để nếu người dùng nhấn "Đăng xuất", form Login sẽ hiện lại
        else:
            # Hiện màn hình Đăng nhập
            login_window = LoginWindow()
            
            # Nếu người dùng bấm tắt cửa sổ Login (mã trả về khác 1) thì thoát app luôn
            if login_window.exec() != 1:
                break
                
            # Lấy thông tin tài khoản sau khi LoginWindow chạy xong và thành công
            current_username = login_window.username
            current_is_admin = login_window.is_admin
            current_is_verified = login_window.is_verified  # [MỚI] Lấy từ màn hình Login vừa đăng nhập
            
        # Khởi tạo Launcher chính với các tham số cũ để tránh lỗi TypeError
        main_window = MainWindow(
            username=current_username, 
            is_admin=current_is_admin
        )
        
        # [ĐÃ SỬA] Gán động trạng thái verify vào thuộc tính của main_window thay vì ép qua hàm khởi tạo
        main_window.is_verified = current_is_verified  
        
        # Hiển thị Launcher chính
        main_window.show()
        
        # Chạy vòng lặp sự kiện cho MainWindow
        app.exec()
        
        # Kiểm tra cờ "logout_requested" từ MainWindow
        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit(0)

if __name__ == "__main__":
    main()