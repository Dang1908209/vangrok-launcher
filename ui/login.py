import json
import os
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from PyQt6.QtCore import QPoint, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Import các module từ core
from core.auth import login_user, register_user, reset_password, save_session

# ================= ĐƯỜNG DẪN CẤU HÌNH GOOGLE OAUTH =================
UI_DIR = os.path.dirname(os.path.abspath(__file__))
LAUNCHER_ROOT = os.path.dirname(UI_DIR)
CLIENT_SECRET_FILE = os.path.join(LAUNCHER_ROOT, "config", "client_secret.json")

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


# ================= LUỒNG CHẠY NGẦM XỬ LÝ GOOGLE AUTH =================
class GoogleLoginWorker(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            if not os.path.exists(CLIENT_SECRET_FILE):
                self.error_signal.emit(
                    f"Authentication file not found!\nPlease ensure the file exists at:\n{CLIENT_SECRET_FILE}"
                )
                return

            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0, prompt="consent")

            response = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {creds.token}"},
            )

            if response.status_code == 200:
                user_info = response.json()
                self.finished_signal.emit(user_info)
            else:
                self.error_signal.emit(
                    "Failed to connect to Google API to fetch profile info."
                )

        except Exception as e:
            self.error_signal.emit(f"Google Login failed:\n{str(e)}")


# ================= MÀN HÌNH ĐĂNG NHẬP CHÍNH =================
class LoginWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vangrok - Authentication")
        # Thay đổi kích thước rộng hơn để chia 2 cột
        self.setFixedSize(800, 500)

        # Bỏ viền cửa sổ mặc định của Windows cho giống Launcher thật
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.old_pos = None

        self.apply_styles()

        self.is_admin = False
        self.is_verified = False
        self.username = ""
        self.google_worker = None

        self.setup_ui()

    def setup_ui(self):
        # Layout chính của toàn bộ cửa sổ (chia theo chiều ngang)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------- CỘT TRÁI (FORM AREA) ----------------
        left_panel = QFrame()
        left_panel.setObjectName("left_panel")
        left_panel.setFixedWidth(450)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 20, 40, 20)

        # Window Controls (Close, Minimize)
        win_ctrl_layout = QHBoxLayout()
        win_ctrl_layout.addStretch()

        btn_min = QPushButton("—")
        btn_min.setObjectName("btn_win_ctrl")
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("btn_win_close")
        btn_close.clicked.connect(self.reject)  # Reject đóng dialog

        win_ctrl_layout.addWidget(btn_min)
        win_ctrl_layout.addWidget(btn_close)
        left_layout.addLayout(win_ctrl_layout)

        left_layout.addStretch()

        # Stacked Widget chứa các trang đăng nhập/đăng ký
        self.stack = QStackedWidget()

        self.page_login = self.build_login_page()
        self.page_register = self.build_register_page()
        self.page_forgot = self.build_forgot_page()

        self.stack.addWidget(self.page_login)  # Index 0
        self.stack.addWidget(self.page_register)  # Index 1
        self.stack.addWidget(self.page_forgot)  # Index 2

        left_layout.addWidget(self.stack)
        left_layout.addStretch()

        # ---------------- CỘT PHẢI (LOGO AREA) ----------------
        right_panel = QFrame()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_logo = QLabel()
        logo_path = os.path.join(LAUNCHER_ROOT, "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.lbl_logo.setPixmap(
                pixmap.scaled(
                    250,
                    250,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.lbl_logo.setText("VANGROK\nLAUNCHER")
            self.lbl_logo.setObjectName("logo_text")
            self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right_layout.addWidget(self.lbl_logo)

        lbl_welcome = QLabel("WELCOME TO VANGROK")
        lbl_welcome.setObjectName("lbl_welcome")
        lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(lbl_welcome)

        # Thêm vào layout chính
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def build_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        lbl_title = QLabel("SIGN IN")
        lbl_title.setObjectName("form_title")
        layout.addWidget(lbl_title)

        self.log_user = QLineEdit()
        self.log_user.setPlaceholderText("Username")
        layout.addWidget(self.log_user)

        self.log_pass = QLineEdit()
        self.log_pass.setPlaceholderText("Password")
        self.log_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.log_pass)

        btn_login = QPushButton("Sign In")
        btn_login.setProperty("class", "primary")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.clicked.connect(self.handle_login)
        layout.addWidget(btn_login)

        divider_layout = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setObjectName("divider")

        lbl_or = QLabel("OR")
        lbl_or.setObjectName("lbl_or")

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setObjectName("divider")

        divider_layout.addWidget(line1)
        divider_layout.addWidget(lbl_or)
        divider_layout.addWidget(line2)
        layout.addLayout(divider_layout)

        self.btn_google = QPushButton("🌐 Sign in with Google")
        self.btn_google.setProperty("class", "google")
        self.btn_google.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_google.clicked.connect(self.handle_google_login)
        layout.addWidget(self.btn_google)

        nav_layout = QHBoxLayout()
        btn_to_reg = QPushButton("Create Account")
        btn_to_reg.setProperty("class", "link")
        btn_to_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_to_reg.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        btn_to_forgot = QPushButton("Forgot Password?")
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl_title = QLabel("REGISTER")
        lbl_title.setObjectName("form_title")
        layout.addWidget(lbl_title)

        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("Username")
        layout.addWidget(self.reg_user)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email Address")
        layout.addWidget(self.reg_email)

        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Password")
        self.reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pass)

        self.reg_pass_confirm = QLineEdit()
        self.reg_pass_confirm.setPlaceholderText("Confirm Password")
        self.reg_pass_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.reg_pass_confirm)

        btn_register = QPushButton("Create Account")
        btn_register.setProperty("class", "primary")
        btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_register.clicked.connect(self.handle_register)
        layout.addWidget(btn_register)

        layout.addSpacing(10)

        btn_back = QPushButton("← Back to Sign In")
        btn_back.setProperty("class", "link")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def build_forgot_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        lbl_title = QLabel("RESET PASSWORD")
        lbl_title.setObjectName("form_title")
        layout.addWidget(lbl_title)

        self.fg_user = QLineEdit()
        self.fg_user.setPlaceholderText("Username")
        layout.addWidget(self.fg_user)

        self.fg_email = QLineEdit()
        self.fg_email.setPlaceholderText("Registered Email")
        layout.addWidget(self.fg_email)

        self.fg_new_pass = QLineEdit()
        self.fg_new_pass.setPlaceholderText("New Password")
        self.fg_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.fg_new_pass)

        btn_reset = QPushButton("Reset Password")
        btn_reset.setProperty("class", "primary")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self.handle_forgot)
        layout.addWidget(btn_reset)

        layout.addSpacing(10)

        btn_back = QPushButton("← Back to Sign In")
        btn_back.setProperty("class", "link")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(btn_back, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    # ================= LOGIC XỬ LÝ =================
    def handle_login(self):
        user = self.log_user.text().strip()
        pwd = self.log_pass.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return

        success, is_admin, is_verified, msg = login_user(user, pwd)

        if success:
            self.is_admin = is_admin
            self.is_verified = is_verified
            self.username = user
            save_session(self.username, self.is_admin, self.is_verified)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)

    def handle_google_login(self):
        self.btn_google.setEnabled(False)
        self.btn_google.setText("⏳ Opening browser...")

        self.google_worker = GoogleLoginWorker()
        self.google_worker.finished_signal.connect(self.on_google_login_success)
        self.google_worker.error_signal.connect(self.on_google_login_error)
        self.google_worker.start()

    def on_google_login_success(self, user_info):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("🌐 Sign in with Google")

        email = user_info.get("email", "")
        full_name = user_info.get("name", "Gamer Vangrok")
        google_username = email.strip().split("@")[0] if email else "GoogleUser"

        # 1. Đăng ký ngầm user Google vào hệ thống để lưu vào cơ sở dữ liệu
        # Bỏ qua kết quả trả về để không báo lỗi nếu user đã tồn tại
        _ = register_user(
            google_username, email, "Google_OAuth_Dummy_Password_123!"
        )

        # 2. Đọc config.json để kiểm tra xem tài khoản này có phải là admin không
        is_admin_check = False
        try:
            config_path = os.path.join(LAUNCHER_ROOT, "config", "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if config.get("admin_email") == email:
                        is_admin_check = True
        except Exception as e:
            print(f"Lỗi đọc config kiểm tra admin: {e}")

        # 3. Cập nhật trạng thái
        self.username = google_username
        self.is_admin = is_admin_check
        self.is_verified = user_info.get("email_verified", False)

        # 4. Lưu lại phiên đăng nhập
        save_session(self.username, self.is_admin, self.is_verified)

        QMessageBox.information(
            self,
            "Success",
            f"Signed in via Google successfully!\nWelcome: {full_name}\nEmail: {email}",
        )
        self.accept()

    def on_google_login_error(self, error_msg):
        self.btn_google.setEnabled(True)
        self.btn_google.setText("🌐 Sign in with Google")
        QMessageBox.critical(self, "OAuth Error", error_msg)

    def handle_register(self):
        user = self.reg_user.text().strip()
        email = self.reg_email.text().strip()
        pwd = self.reg_pass.text().strip()
        pwd_confirm = self.reg_pass_confirm.text().strip()

        if not all([user, email, pwd, pwd_confirm]):
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return

        if pwd != pwd_confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match!")
            return

        success, msg = register_user(user, email, pwd)
        if success:
            QMessageBox.information(
                self,
                "Success",
                "Account created successfully! You can now log in.",
            )
            self.stack.setCurrentIndex(0)
            self.log_user.setText(user)
            self.log_pass.clear()

            self.reg_user.clear()
            self.reg_email.clear()
            self.reg_pass.clear()
            self.reg_pass_confirm.clear()
        else:
            QMessageBox.warning(self, "Error", msg)

    def handle_forgot(self):
        user = self.fg_user.text().strip()
        email = self.fg_email.text().strip()
        new_pwd = self.fg_new_pass.text().strip()

        if not all([user, email, new_pwd]):
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return

        success, msg = reset_password(user, email, new_pwd)
        if success:
            QMessageBox.information(
                self,
                "Success",
                "Password reset successfully! You can now log in.",
            )
            self.stack.setCurrentIndex(0)
            self.log_user.setText(user)
            self.log_pass.clear()

            self.fg_user.clear()
            self.fg_email.clear()
            self.fg_new_pass.clear()
        else:
            QMessageBox.warning(self, "Error", msg)

    # ================= WINDOW DRAGGING =================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and self.old_pos is not None
        ):
            self.move(event.globalPosition().toPoint() - self.old_pos)
            event.accept()

    # ================= STYLESHEET (QSS) =================
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }

            /* --- Left Panel (Form) --- */
            #left_panel {
                background-color: #2b2b2b;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }

            /* --- Right Panel (Logo) --- */
            #right_panel {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1a, stop:1 #111111
                );
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                border-left: 1px solid #ff4d4d;
            }

            #logo_text {
                color: #ff4d4d;
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 2px;
            }

            #lbl_welcome {
                color: #888888;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 3px;
                margin-top: 20px;
            }

            /* --- Typography & Inputs --- */
            QLabel {
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }

            #form_title {
                font-size: 28px;
                font-weight: bold;
                color: #ff4d4d;
                margin-bottom: 20px;
            }

            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px 15px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 1px solid #ff4d4d;
                background-color: #252525;
            }

            /* --- Buttons --- */
            QPushButton.primary {
                background-color: #ff4d4d;
                color: white;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton.primary:hover { background-color: #ff3333; }
            QPushButton.primary:pressed { background-color: #cc0000; }
            
            QPushButton.google {
                background-color: #ffffff;
                color: #333333;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton.google:hover { background-color: #e0e0e0; }
            QPushButton.google:disabled { background-color: #aaaaaa; color: #666666; }
            
            QPushButton.link {
                background: transparent;
                color: #aaaaaa;
                border: none;
                font-size: 13px;
            }
            QPushButton.link:hover { color: #ff4d4d; text-decoration: underline; }

            /* --- Dividers --- */
            #divider { border-top: 1px solid #444444; }
            #lbl_or { color: #888888; font-size: 12px; font-weight: bold; padding: 0 10px; }

            /* --- Window Controls --- */
            #btn_win_ctrl, #btn_win_close {
                background-color: transparent;
                color: #aaaaaa;
                border: none;
                font-size: 14px;
                font-weight: bold;
                min-width: 30px;
                max-height: 25px;
            }
            #btn_win_ctrl:hover { background-color: #555555; color: white; }
            #btn_win_close:hover { background-color: #e81123; color: white; }
        """)