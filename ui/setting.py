import os
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton, QFileDialog, QMessageBox, 
                             QInputDialog, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from core.game_manager import get_install_path, save_install_path, get_storage_info
# Bổ sung import hàm xử lý Database
from core.auth import change_db_username

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SettingsPage(QWidget):
    # Signal bắn thông báo về MainWindow khi đường dẫn cài đặt thay đổi
    path_changed_signal = pyqtSignal()
    
    # Signal bắn thông báo tên mới về MainWindow khi user đổi tên
    username_changed_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_username = ""  # [MỚI] Biến lưu trữ tên người dùng hiện tại
        self.load_fonts()
        self.setup_ui()
        self.update_storage_ui()

    def load_fonts(self):
        # Tự động quét và nạp toàn bộ font trong thư mục assets/fonts
        fonts_dir = os.path.join(BASE_DIR, "assets", "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith(('.ttf', '.otf')):
                    font_path = os.path.join(fonts_dir, font_file)
                    QFontDatabase.addApplicationFont(font_path)

    def setup_ui(self):
        # Dùng đúng tên "Montenegrin Gothic One"
        self.setStyleSheet("QWidget { font-family: 'Montenegrin Gothic One', 'Orbitron', sans-serif; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        
        lbl_title = QLabel("SETTINGS")
        lbl_title.setStyleSheet("font-size: 40px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; margin-bottom: 20px;")
        layout.addWidget(line)
        
        # ==================================================
        # PHẦN 1: THÔNG TIN TÀI KHOẢN
        # ==================================================
        lbl_sec_account = QLabel("👤 TÀI KHOẢN")
        lbl_sec_account.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_sec_account)
        
        account_card = QFrame()
        account_card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; padding: 15px; border: 1px solid #444;")
        account_layout = QHBoxLayout(account_card)
        
        self.lbl_current_user = QLabel("Tên hiển thị: Đang tải...")
        self.lbl_current_user.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        account_layout.addWidget(self.lbl_current_user)
        account_layout.addStretch()
        
        btn_change_name = QPushButton("Đổi Tên Mới")
        btn_change_name.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_name.setStyleSheet("""
            QPushButton { background-color: #555555; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #ff4d4d; }
        """)
        btn_change_name.clicked.connect(self.change_account_username)
        account_layout.addWidget(btn_change_name)
        
        layout.addWidget(account_card)

        # ==================================================
        # PHẦN 2: THƯ MỤC CÀI ĐẶT GAME
        # ==================================================
        lbl_sec1 = QLabel("📁 THƯ MỤC CÀI ĐẶT GAME")
        lbl_sec1.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 25px;")
        layout.addWidget(lbl_sec1)
        
        folder_card = QFrame()
        folder_card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; padding: 15px; border: 1px solid #444;")
        folder_layout = QVBoxLayout(folder_card)
        
        path_layout = QHBoxLayout()
        self.lbl_current_path_display = QLabel(f"Location: {get_install_path()}")
        self.lbl_current_path_display.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        path_layout.addWidget(self.lbl_current_path_display)
        path_layout.addStretch()
        
        btn_change_path = QPushButton("Thay Đổi Thư Mục")
        btn_change_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_path.setStyleSheet("""
            QPushButton { background-color: #555555; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; text-align: center; font-weight: bold; }
            QPushButton:hover { background-color: #ff4d4d; }
        """)
        btn_change_path.clicked.connect(self.change_install_folder)
        path_layout.addWidget(btn_change_path)
        
        btn_open_folder = QPushButton("📂 Mở Thư Mục")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; text-align: center; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn_open_folder.clicked.connect(self.open_install_folder_in_explorer)
        path_layout.addWidget(btn_open_folder)
        
        folder_layout.addLayout(path_layout)
        
        self.lbl_setting_storage_detail = QLabel("Ổ đĩa: Đang tính...")
        self.lbl_setting_storage_detail.setStyleSheet("color: #aaaaaa; font-size: 13px; margin-top: 5px;")
        folder_layout.addWidget(self.lbl_setting_storage_detail)
        
        layout.addWidget(folder_card)
        
        # ==================================================
        # PHẦN 3: TÙY CHỌN KHÁC
        # ==================================================
        lbl_sec2 = QLabel("🚀 TÙY CHỌN KHÁC (SẮP RA MẮT)")
        lbl_sec2.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 25px;")
        layout.addWidget(lbl_sec2)
        
        other_card = QFrame()
        other_card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; padding: 15px; border: 1px solid #444;")
        other_layout = QVBoxLayout(other_card)
        lbl_dummy = QLabel("• Tự động cập nhật game khi khởi động Launcher\n• Chạy Launcher cùng hệ thống Windows\n• Giới hạn tốc độ tải xuống (Bandwidth limit)")
        lbl_dummy.setStyleSheet("color: #888888; font-size: 14px; line-height: 1.5;")
        other_layout.addWidget(lbl_dummy)
        layout.addWidget(other_card)
        
        layout.addStretch()

    # --- CÁC HÀM XỬ LÝ LOGIC ---
    
    def set_current_username(self, username):
        """Hàm này để MainWindow gọi và gán tên user vào Settings khi khởi động"""
        self.current_username = username
        self.lbl_current_user.setText(f"Tên hiển thị: {username}")

    def update_storage_ui(self):
        current_path = get_install_path()
        total_gb, used_gb, free_gb = get_storage_info(current_path)
        
        drive_name = os.path.splitdrive(current_path)[0]
        if not drive_name:
            drive_name = "Disk"
            
        self.lbl_current_path_display.setText(f"Đường dẫn: {current_path}")
        self.lbl_setting_storage_detail.setText(
            f"Ổ đang chọn: {drive_name}  |  Tổng dung lượng: {total_gb} GB  |  Đã dùng: {used_gb} GB  |  Còn trống: {free_gb} GB"
        )

    def change_install_folder(self):
        current_path = get_install_path()
        selected_dir = QFileDialog.getExistingDirectory(
            self, 
            "Chọn Thư Mục Cài Đặt Game Mặc Định", 
            current_path
        )
        
        if selected_dir:
            selected_dir = os.path.normpath(selected_dir)
            save_install_path(selected_dir)
            self.update_storage_ui()
            self.path_changed_signal.emit() 
            
            QMessageBox.information(
                self, 
                "Thành Công", 
                f"Đã thay đổi thư mục cài đặt mặc định sang:\n{selected_dir}"
            )

    def open_install_folder_in_explorer(self):
        current_path = get_install_path()
        if os.path.exists(current_path):
            if os.name == 'nt':
                os.startfile(current_path)
            else:
                subprocess.Popen(['xdg-open', current_path])
        else:
            QMessageBox.warning(self, "Lỗi", "Thư mục hiện tại không tồn tại trên máy tính!")

    # [HOÀN THIỆN] Hàm xử lý đổi tên hiển thị và cập nhật Database
    def change_account_username(self):
        old_name = self.current_username
        
        if not old_name:
            QMessageBox.warning(self, "Lỗi", "Hệ thống chưa tải xong thông tin tài khoản!")
            return

        new_name, ok = QInputDialog.getText(
            self, 
            "Đổi Tên Hiển Thị", 
            "Nhập tên hiển thị mới của bạn:", 
            QLineEdit.EchoMode.Normal, 
            old_name
        )
        
        if ok:
            new_name = new_name.strip()
            
            if not new_name:
                QMessageBox.warning(self, "Lỗi", "Tên hiển thị không được để trống!")
                return
                
            if new_name == old_name:
                QMessageBox.warning(self, "Lỗi", "Tên mới không được trùng với tên hiện tại!")
                return
                
            # XÁC NHẬN TỪ NGƯỜI DÙNG
            warning_msg = (
                f"Bạn có chắc muốn đổi tên thành '{new_name}' không?\n\n"
                f"⚠️ LƯU Ý QUAN TRỌNG: Kể từ lần đăng nhập tiếp theo, bạn BẮT BUỘC "
                f"phải dùng tên '{new_name}' cùng mật khẩu cũ để đăng nhập."
            )
            reply = QMessageBox.question(
                self, 
                "Xác nhận đổi tên", 
                warning_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Gọi hàm cập nhật Database từ core/auth.py
                success, msg = change_db_username(old_name, new_name)
                
                if success:
                    # Cập nhật giao diện trong thẻ Settings
                    self.set_current_username(new_name)
                    
                    # Bắn tín hiệu chứa tên mới về MainWindow
                    self.username_changed_signal.emit(new_name)
                    
                    QMessageBox.information(self, "Thành Công", f"Đổi tên thành công!\nTừ giờ bạn sẽ được gọi là: {new_name}")
                else:
                    QMessageBox.warning(self, "Lỗi Đổi Tên", msg)