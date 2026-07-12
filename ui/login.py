from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QMessageBox, QStackedWidget, QWidget, 
                             QLabel, QFrame, QInputDialog)
from PyQt6.QtCore import Qt
from core.auth import login_user, register_user, reset_password

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vangrok - Xác thực hệ thống")
        self.setFixedSize(350, 520)  # Tăng chiều cao lên một chút cho đẹp
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
            
            /* [MỚI] Style riêng cho nút Đăng nhập Google */
            QPushButton.google {
                background-color: #ffffff; color: #333333; border-radius: 5px;
                padding: 10px; font-size: 14px; font-weight: bold;
            }
            QPushButton.google:hover { background-color: #e0e0e0; }
            
            QPushButton.link {
                background: transparent; color: #aaaaaa; border: none; font-size: 12px;
            }
            QPushButton.link:hover { color: white; text-decoration: underline; }
        """)
        
        self.is_admin = False
        self.username = ""
        
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
        
    # ================= MÀN HÌNH ĐĂNG NHẬP =================
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
        
        # --- [MỚI] ĐƯỜNG KẺ PHÂN CÁCH "HOẶC" ---
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
        
        # --- [MỚI] NÚT ĐĂNG NHẬP BẰNG GOOGLE ---
        btn_google = QPushButton("🌐 Đăng nhập bằng Google")
        btn_google.setProperty("class", "google")
        btn_google.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_google.clicked.connect(self.handle_google_login)
        layout.addWidget(btn_google)
        # ----------------------------------------
        
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

    # ================= MÀN HÌNH ĐĂNG KÝ =================
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

    # ================= MÀN HÌNH QUÊN MẬT KHẨU =================
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
            
        success, is_admin, msg = login_user(user, pwd)
        
        if success:
            self.is_admin = is_admin
            self.username = user
            self.accept()
        else:
            QMessageBox.warning(self, "Lỗi", msg)

    # [MỚI] HÀM XỬ LÝ ĐĂNG NHẬP BẰNG GOOGLE
    def handle_google_login(self):
        """
        Đây là luồng giả lập OAuth Google để bạn test app ngay lập tức.
        Khi triển khai thực tế, bạn sẽ thay đoạn này bằng code mở Trình duyệt (webbrowser) 
        để xác thực với Google API hoặc Firebase Auth.
        """
        email, ok = QInputDialog.getText(
            self, 
            "Xác thực Google OAuth", 
            "Nhập tài khoản Gmail của bạn để tiếp tục:",
            text="gamer.vangrok@gmail.com"
        )
        
        if ok and email.strip():
            if "@" not in email:
                QMessageBox.warning(self, "Lỗi", "Vui lòng nhập định dạng email hợp lệ!")
                return
                
            # Lấy tên trước chữ @ làm username (Ví dụ: gamer.vangrok@gmail.com -> gamer.vangrok)
            google_username = email.strip().split("@")[0]
            
            self.username = google_username
            self.is_admin = False # Mặc định login Google là user thường
            
            QMessageBox.information(self, "Thành công", f"Đăng nhập thành công qua Google!\nXin chào: {google_username}")
            self.accept() # Chuyển thẳng vào Launcher chính

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