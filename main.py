# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.login import LoginWindow
from ui.main_window import MainWindow
# Bổ sung import hàm xử lý kiểm tra đăng nhập tự động
from core.auth import get_current_session

def main():
    app = QApplication(sys.argv)
    
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
    
    # Vòng lặp quản lý luồng sống của ứng dụng (Đăng nhập -> Launcher -> Đăng xuất -> Đăng nhập...)
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
        
        # Chạy vòng lặp sự kiện cho MainWindow (Code sẽ "dừng" ở đây cho đến khi user tắt/đăng xuất launcher)
        app.exec()
        
        # Kiểm tra cờ "logout_requested" từ MainWindow
        # Nếu người dùng bấm X để tắt app -> logout_requested = False -> Break vòng lặp để thoát hẳn
        # Nếu bấm Đăng xuất -> logout_requested = True -> Vòng lặp tiếp tục chạy lại hiển thị LoginWindow
        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit(0)

if __name__ == "__main__":
    main()