import os
import json
import random
import smtplib
import subprocess
from email.mime.text import MIMEText

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QPushButton, QFileDialog, QMessageBox, 
                             QInputDialog, QLineEdit, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFontDatabase

# Import thư viện dịch tự động
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

from core.game_manager import get_install_path, save_install_path, get_storage_info
from core.auth import change_db_username

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_DB_PATH = os.path.join(BASE_DIR, 'config', 'users.json')
SESSION_PATH = os.path.join(BASE_DIR, 'config', 'session.json')


# ================= LUỒNG CHẠY NGẦM GỬI EMAIL OTP =================
class EmailSenderWorker(QThread):
    status_signal = pyqtSignal(bool, str, str)

    def __init__(self, recipient_email, target_username):
        super().__init__()
        self.recipient_email = recipient_email
        self.target_username = target_username

    def run(self):
        try:
            from ui.token_config import GOOGLE_APP_EMAIL, GOOGLE_APP_PASSWORD
        except ImportError:
            self.status_signal.emit(False, "Không tìm thấy cấu hình Google App API trong 'ui/token_config.py'!", "")
            return

        otp_code = str(random.randint(100000, 999999))
        try:
            mail_content = (
                f"Xin chào {self.target_username},\n\n"
                f"Mã OTP để xác thực tài khoản Vangrok Launcher của bạn là: {otp_code}\n"
                f"Vui lòng không chia sẻ mã này cho bất kỳ ai.\n\n"
                f"Trân trọng,\nVangrok Game Launcher Support System."
            )
            msg = MIMEText(mail_content, 'plain', 'utf-8')
            msg['Subject'] = "Vangrok Launcher - Xác thực tài khoản của bạn"
            msg['From'] = GOOGLE_APP_EMAIL
            msg['To'] = self.recipient_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GOOGLE_APP_EMAIL, GOOGLE_APP_PASSWORD)
                server.sendmail(GOOGLE_APP_EMAIL, self.recipient_email, msg.as_string())
                
            self.status_signal.emit(True, "Mã xác thực OTP đã được gửi thành công về Gmail của bạn!", otp_code)
        except Exception as e:
            self.status_signal.emit(False, f"Quá trình gửi mail thất bại: {str(e)}", "")


# ================= LUỒNG CHẠY NGẦM TỰ ĐỘNG DỊCH GIAO DIỆN =================
class TranslatorWorker(QThread):
    """Worker chạy ngầm dịch tự động để không làm đơ giao diện Launcher"""
    # Trả về một từ điển ánh xạ: {văn_bản_gốc: văn_bản_đã_dịch}
    finished_signal = pyqtSignal(dict, str)

    def __init__(self, text_list, target_lang):
        super().__init__()
        self.text_list = text_list
        self.target_lang = target_lang

    def run(self):
        if not GoogleTranslator or self.target_lang == 'vi':
            # Nếu không có thư viện hoặc chọn tiếng Việt thì trả về rỗng (dùng lại tiếng Việt gốc)
            self.finished_signal.emit({}, self.target_lang)
            return

        translator = GoogleTranslator(source='auto', target=self.target_lang)
        result_map = {}
        
        try:
            # Dịch theo lô (batch) để tối ưu tốc độ mạng
            translated_list = translator.translate_batch(self.text_list)
            for orig, trans in zip(self.text_list, translated_list):
                if trans:
                    result_map[orig] = trans
        except Exception as e:
            print(f"Lỗi dịch tự động: {e}")
            
        self.finished_signal.emit(result_map, self.target_lang)


# ================= GIAO DIỆN TRANG CÀI ĐẶT CHÍNH =================
class SettingsPage(QWidget):
    path_changed_signal = pyqtSignal()
    username_changed_signal = pyqtSignal(str)
    # Phát tín hiệu ra MainWindow nếu muốn dịch toàn bộ App (Sidebar, Trang chủ,...)
    language_changed_signal = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_username = ""
        self.user_email = ""
        self.is_verified = False
        self.generated_otp = ""
        self.email_worker = None
        self.translator_worker = None
        self.current_lang = "vi"
        
        self.setObjectName("SettingsPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.load_fonts()
        self.setup_ui()
        self.update_storage_ui()
        self.load_account_data()

    def load_fonts(self):
        fonts_dir = os.path.join(BASE_DIR, "assets", "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith(('.ttf', '.otf')):
                    font_path = os.path.join(fonts_dir, font_file)
                    QFontDatabase.addApplicationFont(font_path)

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget { font-family: 'Montenegrin Gothic One', 'Orbitron', sans-serif; }
            QWidget#SettingsPage {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0.0 #111111, stop: 0.5 #2d2d2d, stop: 1.0 #111111
                );
            }
            QLabel { background: transparent; }
            QComboBox {
                background-color: #333333; color: white; border: 1px solid #555555;
                border-radius: 5px; padding: 5px 10px; font-size: 14px; font-weight: bold;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #2b2b2b; color: white; selection-background-color: #ff4d4d; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        
        lbl_title = QLabel("SETTINGS")
        lbl_title.setStyleSheet("font-size: 40px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: none; border-top: 2px solid #ff4d4d; margin-bottom: 20px; background: transparent;")
        layout.addWidget(line)
        
        # ==================================================
        # PHẦN 1: THÔNG TIN TÀI KHOẢN
        # ==================================================
        lbl_sec_account = QLabel("👤 TÀI KHOẢN")
        lbl_sec_account.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_sec_account)
        
        account_card = QFrame()
        account_card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; padding: 15px; border: 1px solid #444;")
        account_layout = QVBoxLayout(account_card)
        
        user_row = QHBoxLayout()
        self.lbl_current_user = QLabel("Tên hiển thị: Đang tải...")
        self.lbl_current_user.setProperty("is_dynamic", True) # Không dịch text động
        self.lbl_current_user.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        user_row.addWidget(self.lbl_current_user)
        user_row.addStretch()
        
        btn_change_name = QPushButton("Đổi Tên Mới")
        btn_change_name.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_name.setStyleSheet("""
            QPushButton { background-color: #555555; color: white; border-radius: 5px; padding: 6px 15px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #ff4d4d; }
        """)
        btn_change_name.clicked.connect(self.change_account_username)
        user_row.addWidget(btn_change_name)
        account_layout.addLayout(user_row)
        
        inner_line = QFrame()
        inner_line.setFrameShape(QFrame.Shape.HLine)
        inner_line.setStyleSheet("border: none; border-top: 1px solid #3d3d3d; margin: 8px 0px;")
        account_layout.addWidget(inner_line)
        
        verify_row = QHBoxLayout()
        self.lbl_verify_status = QLabel("Xác thực: Đang kiểm tra dữ liệu...")
        self.lbl_verify_status.setProperty("is_dynamic", True) # Không dịch text động
        self.lbl_verify_status.setStyleSheet("color: white; font-size: 14px;")
        verify_row.addWidget(self.lbl_verify_status)
        verify_row.addStretch()
        
        self.btn_verify = QPushButton("Get Verified")
        self.btn_verify.setProperty("is_dynamic", True) # Không dịch text nút trạng thái
        self.btn_verify.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_verify.setStyleSheet("""
            QPushButton { background-color: #ff4d4d; color: white; border-radius: 5px; padding: 6px 15px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: #e60000; }
            QPushButton:disabled { background-color: #444444; color: #888888; border: 1px solid #555; }
        """)
        self.btn_verify.clicked.connect(self.send_verification_otp)
        verify_row.addWidget(self.btn_verify)
        account_layout.addLayout(verify_row)
        
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
        self.lbl_current_path_display.setProperty("is_dynamic", True) # Không dịch text động
        self.lbl_current_path_display.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        path_layout.addWidget(self.lbl_current_path_display)
        path_layout.addStretch()
        
        btn_change_path = QPushButton("Thay Đổi Thư Mục")
        btn_change_path.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_path.setStyleSheet("""
            QPushButton { background-color: #555555; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #ff4d4d; }
        """)
        btn_change_path.clicked.connect(self.change_install_folder)
        path_layout.addWidget(btn_change_path)
        
        btn_open_folder = QPushButton("📂 Mở Thư Mục")
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; border-radius: 5px; padding: 8px 15px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn_open_folder.clicked.connect(self.open_install_folder_in_explorer)
        path_layout.addWidget(btn_open_folder)
        
        folder_layout.addLayout(path_layout)
        
        self.lbl_setting_storage_detail = QLabel("Ổ đĩa: Đang tính...")
        self.lbl_setting_storage_detail.setProperty("is_dynamic", True) # Không dịch text động
        self.lbl_setting_storage_detail.setStyleSheet("color: #aaaaaa; font-size: 13px; margin-top: 5px;")
        folder_layout.addWidget(self.lbl_setting_storage_detail)
        
        layout.addWidget(folder_card)

        # ==================================================
        # PHẦN 3: NGÔN NGỮ & GIAO DIỆN
        # ==================================================
        lbl_sec_lang = QLabel("🌐 NGÔN NGỮ GIAO DIỆN / LANGUAGE (AUTO-TRANSLATE)")
        lbl_sec_lang.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 25px;")
        layout.addWidget(lbl_sec_lang)
        
        lang_card = QFrame()
        lang_card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; padding: 15px; border: 1px solid #444;")
        lang_layout = QHBoxLayout(lang_card)
        
        lbl_lang_desc = QLabel("Chọn ngôn ngữ hiển thị (Hệ thống sẽ tự động dịch Realtime không cần file từ điển):")
        lbl_lang_desc.setStyleSheet("color: #dddddd; font-size: 14px;")
        lang_layout.addWidget(lbl_lang_desc)
        lang_layout.addStretch()
        
        # Nút Dropdown chọn Ngôn Ngữ
        self.cbx_language = QComboBox()
        self.cbx_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cbx_language.addItems([
            "🇻🇳 Tiếng Việt (Mặc định)", 
            "🇺🇸 English (Tiếng Anh)", 
            "🇯🇵 日本語 (Tiếng Nhật)", 
            "🇨🇳 中文 (Tiếng Trung)", 
            "🇰🇷 한국어 (Tiếng Hàn)",
            "🇷🇺 Русский (Tiếng Nga)"
        ])
        
        # Ánh xạ từ index sang mã ngôn ngữ ISO của Google Translate
        self.lang_codes = ["vi", "en", "ja", "zh-CN", "ko", "ru"]
        self.cbx_language.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.cbx_language)
        
        layout.addWidget(lang_card)
        
        # ==================================================
        # PHẦN 4: TÙY CHỌN KHÁC
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

    # ================= CÁC HÀM XỬ LÝ DỊCH TỰ ĐỘNG =================
    def on_language_changed(self, index):
        """Kích hoạt khi người dùng thay đổi lựa chọn trong ComboBox Ngôn Ngữ"""
        target_lang = self.lang_codes[index]
        if target_lang == self.current_lang:
            return
            
        self.current_lang = target_lang
        
        # Phát tín hiệu ra MainWindow để MainWindow biết đường tự dịch toàn app
        self.language_changed_signal.emit(target_lang)
        self.cbx_language.setEnabled(False) # Khóa nút tạm thời lúc đang dịch
        
        # Thu thập toàn bộ văn bản gốc trong trang cần dịch
        texts_to_translate = []
        for widget in self.findChildren((QLabel, QPushButton)):
            # Bỏ qua nút ComboBox và các ký tự đặc biệt không cần dịch
            if widget == self.cbx_language or not hasattr(widget, 'text') or not widget.text().strip():
                continue
                
            # Bỏ qua các text thay đổi động
            if widget.property("is_dynamic"):
                continue
                
            # Luôn lấy văn bản gốc tiếng Việt đã lưu, nếu chưa có thì lưu lại ngay
            orig_text = widget.property("orig_text")
            if not orig_text:
                orig_text = widget.text().strip()
                widget.setProperty("orig_text", orig_text)
                
            if orig_text not in texts_to_translate:
                texts_to_translate.append(orig_text)
                
        # Khởi chạy luồng ngầm dịch tự động
        self.translator_worker = TranslatorWorker(texts_to_translate, target_lang)
        self.translator_worker.finished_signal.connect(self.apply_translation)
        self.translator_worker.start()

    def apply_translation(self, translated_map, target_lang):
        """Cập nhật giao diện Settings sau khi luồng dịch hoàn tất"""
        for widget in self.findChildren((QLabel, QPushButton)):
            if widget == self.cbx_language:
                continue

            orig_text = widget.property("orig_text")
            if orig_text:
                if target_lang == 'vi':
                    widget.setText(orig_text)
                elif orig_text in translated_map:
                    widget.setText(translated_map[orig_text])

        # Mở khóa lại ComboBox sau khi áp dụng xong
        self.cbx_language.setEnabled(True)

        # Cảnh báo nếu dịch thất bại do thiếu thư viện (chỉ cảnh báo 1 lần)
        if not translated_map and target_lang != 'vi':
            QMessageBox.warning(self, "Thiếu Thư Viện", "Bạn cần chạy lệnh:\npip install deep-translator\nđể bật tính năng dịch tự động Google Translate!")

    # ================= CÁC HÀM XỬ LÝ DỮ LIỆU & GIAO DIỆN =================
    def showEvent(self, event):
        super().showEvent(event)
        self.load_account_data()
        self.update_storage_ui()

    def load_account_data(self):
        if os.path.exists(SESSION_PATH):
            try:
                with open(SESSION_PATH, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                    self.current_username = session.get("username", "")
                    self.is_verified = session.get("is_verified", False)
            except Exception as e:
                print(f"Lỗi đọc session.json: {e}")

        if self.current_username and os.path.exists(USERS_DB_PATH):
            try:
                with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                if self.current_username in users:
                    self.user_email = users[self.current_username].get("email", "Không có email")
                    self.is_verified = users[self.current_username].get("is_verified", self.is_verified)
            except Exception as e:
                print(f"Lỗi đọc users.json: {e}")

        if self.current_username:
            self.lbl_current_user.setText(f"Tên hiển thị: {self.current_username}")
            self.refresh_verify_ui()
        else:
            self.lbl_current_user.setText("Tên hiển thị: Chưa đăng nhập")
            self.lbl_verify_status.setText("Trạng thái: Vui lòng đăng nhập lại!")
            self.lbl_verify_status.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
            self.btn_verify.setVisible(False)

    def set_current_username(self, username):
        self.current_username = username
        self.load_account_data()

    def refresh_verify_ui(self):
        if self.is_verified:
            self.lbl_verify_status.setText(f"Email: {self.user_email} | Verified ✅")
            self.lbl_verify_status.setStyleSheet("color: #2ecc71; font-size: 14px; font-weight: bold;")
            self.btn_verify.setEnabled(False)
            self.btn_verify.setText("Đã xác thực")
            self.btn_verify.setVisible(True)
        else:
            self.lbl_verify_status.setText("Trạng thái: Chưa xác thực tài khoản!")
            self.lbl_verify_status.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
            self.btn_verify.setEnabled(True)
            self.btn_verify.setText("Get Verified")
            self.btn_verify.setVisible(True)

    def send_verification_otp(self):
        if not self.user_email or self.user_email == "Không có email":
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy Email tương thích với tài khoản này hệ thống.")
            return
            
        self.btn_verify.setEnabled(False)
        self.btn_verify.setText("⏳ Đang gửi OTP...")
        
        self.email_worker = EmailSenderWorker(self.user_email, self.current_username)
        self.email_worker.status_signal.connect(self.on_otp_sent_result)
        self.email_worker.start()

    def on_otp_sent_result(self, success, message, otp_code):
        if success:
            self.generated_otp = otp_code
            QMessageBox.information(self, "Thành Công", message)
            
            otp_input, ok = QInputDialog.getText(
                self, "Xác thực mã OTP", 
                f"Một mã xác nhận gồm 6 số đã được gửi tới: {self.user_email}\n\nHãy nhập mã OTP vào đây:", 
                QLineEdit.EchoMode.Normal
            )
            
            if ok:
                if otp_input.strip() == self.generated_otp:
                    self.mark_user_as_verified()
                else:
                    QMessageBox.critical(self, "Xác Thực Thất Bại", "Mã OTP bạn nhập không chính xác! Vui lòng thử lại.")
                    self.refresh_verify_ui()
            else:
                self.refresh_verify_ui()
        else:
            QMessageBox.critical(self, "Lỗi Gửi Thư", message)
            self.refresh_verify_ui()

    def mark_user_as_verified(self):
        try:
            if os.path.exists(USERS_DB_PATH):
                with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                if self.current_username in users:
                    users[self.current_username]["is_verified"] = True
                    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
                        json.dump(users, f, indent=4)
            
            if os.path.exists(SESSION_PATH):
                with open(SESSION_PATH, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                if session.get("username") == self.current_username:
                    session["is_verified"] = True
                    with open(SESSION_PATH, 'w', encoding='utf-8') as f:
                        json.dump(session, f, indent=4)
                        
            self.is_verified = True
            self.refresh_verify_ui()
            QMessageBox.information(self, "Chúc Mừng", "Tài khoản của bạn đã được Xác Thực Thành Công! Quyền hạn đã được mở khóa.")
        except Exception as e:
            QMessageBox.warning(self, "Lỗi Hệ Thống", f"Không thể lưu trạng thái xác thực: {str(e)}")

    def update_storage_ui(self):
        current_path = get_install_path()
        total_gb, used_gb, free_gb = get_storage_info(current_path)
        drive_name = os.path.splitdrive(current_path)[0] or "Disk"
            
        self.lbl_current_path_display.setText(f"Đường dẫn: {current_path}")
        self.lbl_setting_storage_detail.setText(
            f"Ổ đang chọn: {drive_name}  |  Tổng dung lượng: {total_gb} GB  |  Đã dùng: {used_gb} GB  |  Còn trống: {free_gb} GB"
        )

    def change_install_folder(self):
        current_path = get_install_path()
        selected_dir = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Cài Đặt Game Mặc Định", current_path)
        if selected_dir:
            selected_dir = os.path.normpath(selected_dir)
            save_install_path(selected_dir)
            self.update_storage_ui()
            self.path_changed_signal.emit() 
            QMessageBox.information(self, "Thành Công", f"Đã thay đổi thư mục cài đặt mặc định sang:\n{selected_dir}")

    def open_install_folder_in_explorer(self):
        current_path = get_install_path()
        if os.path.exists(current_path):
            if os.name == 'nt':
                os.startfile(current_path)
            else:
                subprocess.Popen(['xdg-open', current_path])
        else:
            QMessageBox.warning(self, "Lỗi", "Thư mục hiện tại không tồn tại trên máy tính!")

    def change_account_username(self):
        old_name = self.current_username
        if not old_name:
            QMessageBox.warning(self, "Lỗi", "Hệ thống chưa tải xong thông tin tài khoản!")
            return

        new_name, ok = QInputDialog.getText(self, "Đổi Tên Hiển Thị", "Nhập tên hiển thị mới của bạn:", QLineEdit.EchoMode.Normal, old_name)
        if ok:
            new_name = new_name.strip()
            if not new_name or new_name == old_name:
                QMessageBox.warning(self, "Lỗi", "Tên mới không hợp lệ hoặc trùng tên cũ!")
                return
                
            warning_msg = f"Bạn có chắc muốn đổi tên thành '{new_name}' không?\n\n⚠️ Lưu ý đăng nhập lại với tên mới."
            reply = QMessageBox.question(self, "Xác nhận", warning_msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = change_db_username(old_name, new_name)
                if success:
                    self.set_current_username(new_name)
                    self.username_changed_signal.emit(new_name)
                    QMessageBox.information(self, "Thành Công", f"Đổi tên thành công sang: {new_name}")
                else:
                    QMessageBox.warning(self, "Lỗi Đổi Tên", msg)