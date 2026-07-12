import sys
from PyQt6.QtWidgets import QApplication
from ui.login import LoginWindow
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    while True:
        # 1. Gọi màn hình Đăng nhập
        login_window = LoginWindow()
        
        # Nếu người dùng bấm tắt cửa sổ Login (mã trả về khác 1) thì thoát app luôn
        if login_window.exec() != 1:
            break
            
        # 2. Khởi tạo và hiển thị Launcher chính
        main_window = MainWindow(
            username=login_window.username, 
            is_admin=login_window.is_admin
        )
        main_window.show()
        
        # 3. Chạy vòng lặp sự kiện cho MainWindow
        app.exec()
        
        # 4. Kiểm tra cờ "logout_requested" từ MainWindow
        # Nếu người dùng bấm X để tắt app -> logout_requested = False -> Break vòng lặp để thoát
        # Nếu bấm Đăng xuất -> logout_requested = True -> Vòng lặp tiếp tục chạy lại LoginWindow()
        if not getattr(main_window, "logout_requested", False):
            break

    sys.exit(0)

if __name__ == "__main__":
    main()