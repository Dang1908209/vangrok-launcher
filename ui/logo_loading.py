import sys
import time
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow  # File giao diện chính của bạn

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Hiển thị màn hình Loading/Logo ngay lập tức
    pixmap = QPixmap("assets/images/logo.png") # Đường dẫn ảnh logo của bạn
    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    
    # Thay vì dùng time.sleep (làm đơ app), bạn cho app xử lý các tiến trình khởi tạo
    app.processEvents() 
    
    # 2. Khởi tạo giao diện chính (nhưng chưa hiển thị)
    main_win = MainWindow()
    
    # Giả lập hoặc xử lý việc load font, đọc session.json, kiểm tra ổ đĩa...
    time.sleep(2) # Đoạn này sau này thay bằng logic load data thực tế nhé
    
    # 3. Mở giao diện chính và tắt màn hình loading
    main_win.show()
    splash.finish(main_win)
    
    sys.exit(app.exec())