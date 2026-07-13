# ui/login.py

import os
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QMessageBox, QStackedWidget, QWidget, 
                             QLabel, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Import thư viện OAuth chính chủ của Google
from google_auth_oauthlib.flow import InstalledAppFlow
from core.auth import login_user, register_user, reset_password, save_session

# ================= ĐƯỜNG DẪN CẤU HÌNH GOOGLE OAUTH =================
UI_DIR = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_ROOT = os.path.dirname(UI_DIR)
CLIENT_SECRET_FILE = os.path.join(LAUNCHER_ROOT, "config", "client_secret.json")

# Các quyền hạn muốn xin từ tài khoản Google của game thủ
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# ================= LUỒNG CHẠY NGẦM XỬ LÝ GOOGLE AUTH =================
class GoogleLoginWorker(QThread):
    finished_signal = pyqtSignal(dict)  # Bắn data user về main UI khi thành công
    error_signal = pyqtSignal(str)      # Bắn thông báo lỗi về nếu có biến

    def run(self):
        try:
            # Kiểm tra xem mày đã ném file vào thư mục config chưa
            if not os.path.exists(CLIENT_SECRET_FILE):
                self.error_signal.emit(
                    f"Không tìm thấy file xác thực!\nVui lòng đảm bảo file tồn tại tại:\n{CLIENT_SECRET_FILE}"
                )
                return

            # Khởi tạo luồng OAuth từ file cấu hình JSON trong thư mục config
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            
            # port=0 để hệ thống tự cấp một cổng local trống ngẫu nhiên làm cổng hồi đáp (callback server)
            creds = flow.run_local_server(port=0, prompt='consent')

            # Gửi Request lấy thông tin tài khoản sau khi user đăng nhập trên web thành công
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {creds.token}'}
            )

            if response.status_code == 200:
                user_info = response.json()
                self.finished_signal.emit(user_info)
            else:
                self.error_signal.emit("Không thể kết nối tới Google API để lấy thông tin profile.")
                
        except Exception as e:
            self.error_signal.emit(f"Quá trình đăng nhập Google thất bại:\n{str(e)}")

# ================= MÀN HÌNH ĐĂNG NHẬP CHÍNH =================
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vangrok - Xác thực hệ thống")
        self.setFixedSize(350, 520)  
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: white; font-family: 'Segoe UI', Arial; }
            QLineEdit {
                background-color: #3b3b3b; color: white; border: 1px solid #555;
                border-radius: 5px; padding: 10px; font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #ff4d4d; }
            
            QPushButton.primary {
                background-color: #ff4d4d; color: white; border-radius: 5px;
                padding: 10px; font-size: 14px; font-weight: bold;
            }
            QPushButton.primary:hover { background-color: #e60000; }
            
            QPushButton.google {
                background-color: #ffffff; color: #333333; border-radius: 5px;
                padding: 10px; font-size: 14px; font-weight: bold;
            }
            QPushButton.google:hover { background-color: #e0e0e0; }
            QPushButton.google:disabled { background-color: #aaaaaa; color: #666666; }
            
            QPushButton.link {
                background: transparent; color: #aaaaaa; border: none; font-size: 12px;
            }
            QPushButton.link:hover { color: white; text-decoration: underline; }
        """)
        
        self.is_admin = False
        self.is_verified = False  # [MỚI] Khởi tạo biến lưu trạng thái verify của user
        self.username = ""
        self.google_worker = None  
        
        self.stack = QStackedWidget(self)
        
        self.page_login = self.build_login_page()
        self.page_register = self.build_register_page()
        self.page_forgot = self.build_forgot_page()
        
        self.stack.addWidget(self.page_login)    # Index 0
        self.stack.addWidget(self.page_register) # Index 1
        self.stack.addWidget(self.page_forgot)   # Index 2
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        self.setLayout(layout)
        
    def build_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("ĐĂNG NHẬP")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ff4d4d; margin-bottom: 15px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        self.log_user = QLineEdit()
        self.log_user.setPlaceholderText("Tên đăng nhập")
        layout.addWidget(self.log_user)
        
        self.log_pass = QLineEdit()
        self.log_pass.setPlaceholderText("Mật khẩu")
        self.log_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.log_pass)
        
        btn_login = QPushButton("Đăng nhập")
        btn_login.setProperty("class", "primary")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self.handle_login)
        layout.addWidget(btn_login)
        
        divider_layout = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("border-top: 1px solid #555;")
        
        lbl_or = QLabel("HOẶC")
        lbl_or.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        lbl_or.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("border-top: 1px solid #555;")
        
        divider_layout.addWidget(line1)
        divider_layout.addWidget(lbl_or)
        divider_layout.addWidget(line2)
        layout.addLayout(divider_layout)
        
        self.btn_google = QPushButton("🌐 Đăng nhập bằng Google")
        self.btn_google.setProperty("class", "google")
        self.btn_google.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_google.clicked.connect(self.handle_google_login)
        layout.addWidget(self.btn_google)
        
        nav_layout = QHBoxLayout()
        btn_to_reg = QPushButton("Đăng ký")
        btn_to_reg.setProperty("class", "link")
        btn_to_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_to_reg.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        
        btn_to_forgot = QPushButton("Quên mật khẩu?")
        btn_to_forgot.setProperty("class", "link")
        btn_to_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_to_forgot.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        
        nav_layout.addWidget(btn_to_reg)
        nav_layout.addStretch()
        nav_layout.addWidget(btn_to_forgot)
        layout.addLayout(nav_layout)
        
        return page

    def build_register_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("ĐĂNG KÝ TÀI KHOẢN")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ff4d4d; margin-bottom: 15px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Tên đăng nhập")
        layout.addWidget(self.reg_user)
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email của bạn")
        layout.addWidget(self.reg_email)
        
        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Mật khẩu")
        self.reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pass)
        
        self.reg_pass_confirm = QLineEdit()
        self.reg_pass_confirm.setPlaceholderText("Xác nhận mật khẩu")
        self.reg_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pass_confirm)
        
        btn_register = QPushButton("Tạo tài khoản")
        btn_register.setProperty("class", "primary")
        btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_register.clicked.connect(self.handle_register)
        layout.addWidget(btn_register)
        
        btn_back = QPushButton("← Quay lại đăng nhập")
        btn_back.setProperty("class", "link")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_back)
        
        return page

    def build_forgot_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel("KHÔI PHỤC MẬT KHẨU")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ff4d4d; margin-bottom: 15px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        self.fg_user = QLineEdit()
        self.fg_user.setPlaceholderText("Tên đăng nhập")
        layout.addWidget(self.fg_user)
        
        self.fg_email = QLineEdit()
        self.fg_email.setPlaceholderText("Email đã đăng ký")
        layout.addWidget(self.fg_email)
        
        self.fg_new_pass = QLineEdit()
        self.fg_new_pass.setPlaceholderText("Mật khẩu mới")
        self.fg_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.fg_new_pass)
        
        btn_reset = QPushButton("Đổi mật khẩu")
        btn_reset.setProperty("class", "primary")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.handle_forgot)
        layout.addWidget(btn_reset)
        
        btn_back = QPushButton("← Quay lại đăng nhập")
        btn_back.setProperty("class", "link")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_back)
        
        return page

    # ================= LOGIC XỬ LÝ =================
    def handle_login(self):
        user = self.log_user.text().strip()
        pwd = self.log_pass.text().strip()
        
        if not user or not pwd:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đủ thông tin!")
            return
            
        # [CẬP NHẬT] Đón nhận thêm biến is_verified từ hàm login_user mới
        success, is_admin, is_verified, msg = login_user(user, pwd)
        
        if success:
            self.is_admin = is_admin
            self.is_verified = is_verified  # [MỚI] Lưu trạng thái verify
            self.username = user
            # [CẬP NHẬT] Lưu session đi kèm giá trị is_verified
            save_session(self.username, self.is_admin, self.is_verified) 
            self.accept()
        else:
            QMessageBox.warning(self, "Lỗi", msg)

    def handle_google_login(self):
        self.btn_google.setEnabled(False)
        self.btn_google.setText("⏳ Đang mở trình duyệt...")
        
        self.google_worker = GoogleLoginWorker()
        self.google_worker.finished_signal.connect(self.on_google_login_success)
        self.google_worker.error_signal.connect(self.on_google_login_error)
        self.google_worker.start()

    def on_google_login_success(self, user_info):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("🌐 Đăng nhập bằng Google")
        
        email = user_info.get("email", "")
        full_name = user_info.get("name", "Gamer Vangrok")
        
        google_username = email.strip().split("@")[0] if email else "GoogleUser"
        
        self.username = google_username
        self.is_admin = False 
        
        # [MỚI] Nếu đăng nhập bằng Google, kiểm tra xem email của họ đã được Google xác thực (email_verified) chưa
        self.is_verified = user_info.get("email_verified", False)
        
        # [CẬP NHẬT] Lưu session có kèm is_verified của tài khoản Google
        save_session(self.username, self.is_admin, self.is_verified)
        
        QMessageBox.information(self, "Thành công", f"Đăng nhập thành công qua Google!\nXin chào: {full_name}\nEmail: {email}")
        self.accept() 

    def on_google_login_error(self, error_msg):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("🌐 Đăng nhập bằng Google")
        QMessageBox.critical(self, "Lỗi OAuth", error_msg)

    def handle_register(self):
        user = self.reg_user.text().strip()
        email = self.reg_email.text().strip()
        pwd = self.reg_pass.text().strip()
        pwd_confirm = self.reg_pass_confirm.text().strip()
        
        if not all([user, email, pwd, pwd_confirm]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng điền đầy đủ thông tin!")
            return
            
        if pwd != pwd_confirm:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu xác nhận không khớp!")
            return
            
        success, msg = register_user(user, email, pwd)
        if success:
            QMessageBox.information(self, "Thành công", msg)
            self.stack.setCurrentIndex(0)
            self.log_user.setText(user)
            self.log_pass.clear()
            
            self.reg_user.clear(); self.reg_email.clear()
            self.reg_pass.clear(); self.reg_pass_confirm.clear()
        else:
            QMessageBox.warning(self, "Lỗi", msg)

    def handle_forgot(self):
        user = self.fg_user.text().strip()
        email = self.fg_email.text().strip()
        new_pwd = self.fg_new_pass.text().strip()
        
        if not all([user, email, new_pwd]):
            QMessageBox.warning(self, "Lỗi", "Vui lòng điền đầy đủ thông tin!")
            return
            
        success, msg = reset_password(user, email, new_pwd)
        if success:
            QMessageBox.information(self, "Thành công", msg)
            self.stack.setCurrentIndex(0)
            self.log_user.setText(user)
            self.log_pass.clear()
            
            self.fg_user.clear(); self.fg_email.clear(); self.fg_new_pass.clear()
        else:
            QMessageBox.warning(self, "Lỗi", msg)