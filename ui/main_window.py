import os
import subprocess  # Thêm thư viện này để hỗ trợ nút Mở folder

from ui.add_game_dialog import AddGameDialog
from core.updater import check_launcher_update, LauncherUpdaterWorker
# [MỚI] Thêm QMenu từ QtWidgets
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QPushButton, QFrame, QStackedWidget, 
                             QProgressBar, QLineEdit, QMessageBox, QFileDialog, QMenu)
# [MỚI] Thêm QAction từ QtGui và QPoint từ QtCore
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QAction
from ui.widgets.game_card import GameCard
from core.game_manager import get_all_games, get_install_path, save_install_path, get_storage_info

# [MỚI] Import màn hình Login
from ui.login import LoginWindow 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MainWindow(QMainWindow):
    def __init__(self, username, is_admin):
        super().__init__()
        self.username = username
        self.is_admin = is_admin
        self.games_data = get_all_games() # Load data game từ JSON
        
        self.setWindowTitle("Vangrok Launcher")
        self.resize(1100, 650)
        
        # 1. Ẩn thanh tiêu đề mặc định của Windows (Frameless Window)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.old_pos = None  # Biến lưu tọa độ chuột để kéo thả cửa sổ
        
        self.setup_ui()
        self.apply_styles()
        
        # Cập nhật dung lượng thật của ổ đĩa ngay khi mở ứng dụng
        self.update_storage_ui()

        self.btn_update_launcher = QPushButton("Cập nhật Launcher!", self)
        self.btn_update_launcher.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_update_launcher.hide() 
        self.btn_update_launcher.clicked.connect(self.start_update_launcher)
        
        # Chạy kiểm tra version
        self.check_version()
        
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ================= SIDEBAR TRÁI =================
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        
        self.lbl_logo = QLabel()
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.lbl_logo.setPixmap(pixmap.scaled(180, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_logo.setText("WM VANGROK")
            self.lbl_logo.setObjectName("logo_text")
        
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.lbl_logo)
        
        btn_store = QPushButton("🎮Store")
        btn_store.setObjectName("nav_btn_active")
        btn_store.clicked.connect(lambda: self.content_area.setCurrentIndex(0))
        sidebar_layout.addWidget(btn_store)
        
        lbl_library = QLabel("LIBRARY")
        lbl_library.setObjectName("library_title")
        lbl_library.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(lbl_library)
        
        for game in self.games_data:
            # ĐÃ SỬA: Dùng "name" thay vì "title"
            btn_game = QPushButton(game["name"])
            btn_game.clicked.connect(lambda checked, g=game: self.show_game_detail(g))
            sidebar_layout.addWidget(btn_game)
        
        sidebar_layout.addStretch()
        
        # --- NÚT SETTINGS (Chuyển sang trang Index 2) ---
        self.btn_setting = QPushButton("⚙ Setting")
        self.btn_setting.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_setting.clicked.connect(lambda: self.content_area.setCurrentIndex(2))
        sidebar_layout.addWidget(self.btn_setting)
        
        main_layout.addWidget(sidebar)
        
        # ================= CONTENT PHẢI =================
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 10, 0)
        top_layout.addStretch()
        
        self.btn_add_game = QPushButton("+ Thêm trò chơi")
        self.btn_add_game.setObjectName("btn_admin")
        self.btn_add_game.setVisible(self.is_admin)
        top_layout.addWidget(self.btn_add_game)
        self.btn_add_game.clicked.connect(self.open_add_game_dialog)
        
        # [MỚI] THAY THẾ LABEL USER CŨ BẰNG NÚT USER PROFILE CÓ MENU
        self.btn_user = QPushButton(f"👤 {self.username.upper()}  ▼")
        self.btn_user.setObjectName("btn_user")
        self.btn_user.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Tạo Dropdown Menu cho nút User
        user_menu = QMenu(self)
        user_menu.setObjectName("user_menu")
        
        action_change_acc = QAction("🔄  Change Account", self)
        action_change_acc.triggered.connect(self.change_account)
        
        action_logout = QAction("🚪  Log Out", self)
        action_logout.triggered.connect(self.log_out)
        
        user_menu.addAction(action_change_acc)
        user_menu.addSeparator() # Đường kẻ ngang phân cách
        user_menu.addAction(action_logout)
        
        # Gắn menu vào nút
        self.btn_user.setMenu(user_menu)
        top_layout.addWidget(self.btn_user)
        # -----------------------------------------------------------------
        
        # 2. Thêm các nút điều khiển cửa sổ (Minimize, Maximize, Close)
        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("☐")
        self.btn_close = QPushButton("✕")
        
        self.btn_min.setObjectName("btn_win_ctrl")
        self.btn_max.setObjectName("btn_win_ctrl")
        self.btn_close.setObjectName("btn_win_close")
        
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.close)
        
        top_layout.addWidget(self.btn_min)
        top_layout.addWidget(self.btn_max)
        top_layout.addWidget(self.btn_close)
        
        right_layout.addWidget(top_bar)
        
        self.content_area = QStackedWidget()
        self.build_store_page()       # Index 0: Store
        self.build_detail_page()      # Index 1: Detail Game
        self.build_settings_page()    # Index 2: Settings Page
        
        right_layout.addWidget(self.content_area)
        main_layout.addWidget(right_panel)

    def change_account(self):
        """Bật cờ yêu cầu đăng xuất và đóng Launcher"""
        self.logout_requested = True
        self.close()

    def log_out(self):
        """Hỏi xác nhận trước khi đăng xuất"""
        reply = QMessageBox.question(
            self, 
            "Đăng xuất", 
            "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested = True
            self.close()
            self.login_win = LoginWindow()
            self.login_win.show()
    # ---------------------------------------------------------------

    # 3. Các hàm xử lý kéo thả cửa sổ và phóng to/thu nhỏ
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.old_pos is not None:
            self.move(event.globalPosition().toPoint() - self.old_pos)
            event.accept()

    def build_store_page(self):
        store_page = QWidget()
        layout = QVBoxLayout(store_page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        lbl_store = QLabel("STORE")
        lbl_store.setStyleSheet("font-size: 56px; font-weight: bold; color: white; letter-spacing: 2px;")
        lbl_desc = QLabel("Install and purchase items")
        lbl_desc.setStyleSheet("font-size: 18px; color: white;")
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid white; max-width: 200px;")
        
        title_layout.addWidget(lbl_store)
        title_layout.addWidget(line)
        title_layout.addWidget(lbl_desc)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # --- KHU VỰC HIỂN THỊ DUNG LƯỢNG Ổ ĐĨA ---
        storage_frame = QFrame()
        storage_frame.setObjectName("storage_frame")
        storage_layout = QVBoxLayout(storage_frame)
        
        self.lbl_storage = QLabel("Storage: Đang tính...\nfree")
        self.lbl_storage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_storage.setStyleSheet("color: white; font-weight: bold;")
        
        self.progress_storage = QProgressBar()
        self.progress_storage.setTextVisible(False)
        self.progress_storage.setFixedHeight(10)
        self.progress_storage.setObjectName("storage_progress")
        
        storage_layout.addWidget(self.lbl_storage)
        storage_layout.addWidget(self.progress_storage)
        header_layout.addWidget(storage_frame)
        
        layout.addLayout(header_layout)
        
        search_layout = QHBoxLayout()
        search_layout.addStretch()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("🔍 SEARCH")
        search_bar.setFixedWidth(200)
        search_bar.setObjectName("search_bar")
        search_layout.addWidget(search_bar)
        layout.addLayout(search_layout)
        
        banner = QFrame()
        banner.setObjectName("banner")
        banner.setFixedHeight(140)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 20, 20, 20)
        
        # ĐÃ SỬA: Đảm bảo dùng key "name"
        banner_title = self.games_data[0]["name"] if self.games_data else "Game"
        banner_ver = self.games_data[0]["version"] if self.games_data else "x.x.x"
        banner_size = self.games_data[0]["size"] if self.games_data else "N/A GB"
        
        banner_info = QVBoxLayout()
        lbl_banner_title = QLabel(banner_title)
        lbl_banner_title.setStyleSheet("font-size: 24px; color: white; font-weight: bold;")
        lbl_banner_ver = QLabel(f"Ver {banner_ver}")
        lbl_banner_ver.setStyleSheet("color: white;")
        banner_info.addStretch()
        banner_info.addWidget(lbl_banner_title)
        banner_info.addWidget(lbl_banner_ver)
        
        banner_center = QLabel("IMAGE BANNER")
        banner_center.setStyleSheet("font-size: 20px; color: white;")
        banner_center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        banner_action = QVBoxLayout()
        banner_action.addStretch()
        lbl_banner_size = QLabel(banner_size)
        lbl_banner_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_banner_size.setStyleSheet("color: white;")
        btn_banner_install = QPushButton("Install")
        btn_banner_install.setFixedWidth(120)
        btn_banner_install.setObjectName("btn_action")
        banner_action.addWidget(lbl_banner_size)
        banner_action.addWidget(btn_banner_install)
        
        banner_layout.addLayout(banner_info)
        banner_layout.addWidget(banner_center, stretch=1)
        banner_layout.addLayout(banner_action)
        layout.addWidget(banner)
        
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(20)
        
        for game in self.games_data:
            card = GameCard(game)
            card.card_clicked.connect(self.show_game_detail)
            grid_layout.addWidget(card)
            
        grid_layout.addStretch()
        layout.addLayout(grid_layout)
        layout.addStretch()
        
        self.content_area.addWidget(store_page)

    def build_detail_page(self):
        self.detail_page = QWidget()
        layout = QVBoxLayout(self.detail_page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        btn_back = QPushButton("⬅ Quay lại Store")
        btn_back.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; text-align: left; padding: 0px; margin-bottom: 15px;")
        btn_back.setFixedWidth(180)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(lambda: self.content_area.setCurrentIndex(0))
        layout.addWidget(btn_back)
        
        self.detail_banner = QLabel()
        self.detail_banner.setFixedHeight(220)
        self.detail_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_banner.setStyleSheet("background-color: #2b2b2b; border-radius: 10px; border: 1px solid #555;")
        layout.addWidget(self.detail_banner)
        
        header_layout = QHBoxLayout()
        self.detail_title = QLabel("Game Title")
        self.detail_title.setStyleSheet("font-size: 38px; font-weight: bold; color: white; margin-top: 15px;")
        header_layout.addWidget(self.detail_title)
        
        header_layout.addStretch()
        
        self.detail_btn_action = QPushButton("Install")
        self.detail_btn_action.setFixedSize(160, 45)
        self.detail_btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn_action.setStyleSheet("background-color: #ff4d4d; color: white; font-size: 18px; font-weight: bold; border-radius: 5px;")
        header_layout.addWidget(self.detail_btn_action)
        
        layout.addLayout(header_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 1px solid #555; margin: 15px 0;")
        layout.addWidget(line)
        
        lbl_about = QLabel("VỀ TRÒ CHƠI NÀY")
        lbl_about.setStyleSheet("color: #aaaaaa; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(lbl_about)
        
        self.detail_desc = QLabel("Mô tả game sẽ hiện ở đây...")
        self.detail_desc.setStyleSheet("color: #dddddd; font-size: 16px; line-height: 1.6;")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.detail_desc, stretch=1)
        
        self.content_area.addWidget(self.detail_page)

    def build_settings_page(self):
        settings_page = QWidget()
        layout = QVBoxLayout(settings_page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        lbl_title = QLabel("SETTINGS")
        lbl_title.setStyleSheet("font-size: 40px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; margin-bottom: 20px;")
        layout.addWidget(line)
        
        lbl_sec1 = QLabel("📁 THƯ MỤC CÀI ĐẶT GAME")
        lbl_sec1.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; margin-top: 10px;")
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
        self.content_area.addWidget(settings_page)

    def update_storage_ui(self):
        current_path = get_install_path()
        total_gb, used_gb, free_gb = get_storage_info(current_path)
        
        drive_name = os.path.splitdrive(current_path)[0]
        if not drive_name:
            drive_name = "Disk"
            
        self.lbl_storage.setText(f"Drive {drive_name}\n{free_gb} GB free")
        self.progress_storage.setMaximum(total_gb)
        self.progress_storage.setValue(used_gb)
        
        if hasattr(self, 'lbl_current_path_display'):
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
            
            QMessageBox.information(
                self, 
                "Thành Công", 
                f"Đã thay đổi thư mục cài đặt mặc định sang:\n{selected_dir}"
            )

    def open_install_folder_in_explorer(self):
        current_path = get_install_path()
        if os.path.exists(current_path):
            os.startfile(current_path)
        else:
            QMessageBox.warning(self, "Lỗi", "Thư mục hiện tại không tồn tại trên máy tính!")

    def show_game_detail(self, game_data):
        self.detail_title.setText(game_data.get("name", "Unknown Game"))
        
        status_text = game_data.get("status", "Install")
        self.detail_btn_action.setText(status_text)
        if status_text == "Play":
            self.detail_btn_action.setStyleSheet("background-color: #27ae60; color: white; font-size: 18px; font-weight: bold; border-radius: 5px;")
        elif status_text == "Update":
            self.detail_btn_action.setStyleSheet("background-color: #f39c12; color: white; font-size: 18px; font-weight: bold; border-radius: 5px;")
        else:
            self.detail_btn_action.setStyleSheet("background-color: #ff4d4d; color: white; font-size: 18px; font-weight: bold; border-radius: 5px;")
            
        default_desc = "Trò chơi này hiện chưa có bài viết mô tả chi tiết từ quản trị viên Vangrok.\n\nHãy nhấn nút bên trên để cài đặt và trải nghiệm cùng bạn bè ngay!"
        self.detail_desc.setText(game_data.get("description", default_desc))
        
        banner_path = os.path.join(BASE_DIR, game_data.get("banner", ""))
        thumb_path = os.path.join(BASE_DIR, game_data.get("thumbnail", ""))
        
        target_img = banner_path if (os.path.exists(banner_path) and os.path.isfile(banner_path)) else thumb_path
        
        if os.path.exists(target_img) and os.path.isfile(target_img):
            pixmap = QPixmap(target_img)
            self.detail_banner.setPixmap(
                pixmap.scaled(850, 220, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            )
            self.detail_banner.setText("")
        else:
            self.detail_banner.clear()
            # ĐÃ SỬA: Đảm bảo dùng "name" ở text dự phòng
            self.detail_banner.setText(f"IMAGE BANNER: {game_data.get('name', '').upper()}")
            self.detail_banner.setStyleSheet("background-color: #2b2b2b; color: white; font-size: 24px; font-weight: bold; border-radius: 10px; border: 1px solid #555;")
            
        self.content_area.setCurrentIndex(1)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #3b3b3b; }
            #sidebar {
                background-color: #2b2b2b;
                border-right: 1px solid #ff4d4d;
            }
            #right_panel { background-color: #4a4a4a; }
            QLabel { font-family: 'Segoe UI', Arial; }
            
            QPushButton {
                background-color: transparent; color: white; border: none;
                padding: 12px; font-size: 18px; text-align: left; padding-left: 40px;
            }
            QPushButton:hover { background-color: #444444; }
            #nav_btn_active { background-color: #555555; border-radius: 5px; }
            
            #library_title { color: #ff4d4d; font-size: 22px; margin-top: 20px; margin-bottom: 10px; }
            
            #btn_admin {
                background-color: transparent; border: 1px solid #ff4d4d; color: #ff4d4d;
                border-radius: 5px; padding: 5px 15px; text-align: center; font-size: 12px;
            }
            #btn_admin:hover { background-color: #ff4d4d; color: white; }
            
            #storage_frame {
                border: 1px solid #ff4d4d; border-radius: 5px; background-color: #3b3b3b;
                padding: 10px; min-width: 130px;
            }
            #storage_progress { border: none; background-color: #2b2b2b; border-radius: 5px; }
            #storage_progress::chunk { background-color: #3498db; border-radius: 5px; }
            
            #banner { background-color: #2b2b2b; border-radius: 15px; margin-top: 10px; margin-bottom: 20px; }
            
            #game_card { 
                background-color: #2b2b2b; 
                border-radius: 8px; 
                border: 1px solid transparent; 
            }
            #game_card:hover { 
                background-color: #383838; 
                border: 1px solid #ff4d4d; 
            }
            
            #btn_action { border-radius: 5px; padding: 5px; font-size: 14px; text-align: center; margin: 0px 5px 5px 5px; }
            
            #search_bar {
                background-color: #2b2b2b; color: white; border: none;
                border-radius: 10px; padding: 5px 15px; font-size: 14px; margin-bottom: 10px;
            }

            /* Style cho 3 nút điều khiển góc trên bên phải */
            #btn_win_ctrl, #btn_win_close {
                background-color: transparent; color: #aaaaaa; border: none;
                padding: 5px 12px; font-size: 14px; font-weight: bold;
                text-align: center; border-radius: 0px; min-width: 35px; max-height: 30px;
            }
            #btn_win_ctrl:hover { background-color: #555555; color: white; }
            #btn_win_close:hover { background-color: #e81123; color: white; }

            /* [MỚI] Style cho Nút User Profile */
            #btn_user {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555555;
                border-radius: 15px;
                padding: 5px 15px;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
                margin-right: 15px;
            }
            #btn_user:hover {
                background-color: #383838;
                border: 1px solid #ff4d4d;
            }
            /* Ẩn mũi tên xổ xuống mặc định xấu xí của PyQt để dùng ký tự ▼ cho đồng bộ */
            #btn_user::menu-indicator {
                image: none; 
            }

            /* [MỚI] Style cho Dropdown Menu (QMenu) */
            QMenu {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #ff4d4d;
                border-radius: 8px;
                padding: 5px 0px;
            }
            QMenu::item {
                padding: 8px 25px 8px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QMenu::item:selected {
                background-color: #ff4d4d;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444444;
                margin: 4px 0px;
            }
        """)

    def open_add_game_dialog(self):
        dialog = AddGameDialog(self)
        dialog.exec()

    def check_version(self):
        needs_update, new_version = check_launcher_update()
        if needs_update:
            self.btn_update_launcher.setText(f"Có bản mới (v{new_version}) - Cập nhật ngay!")
            self.btn_update_launcher.show() # Hiện nút lên để người dùng bấm

    def start_update_launcher(self):
        # Khi người dùng nhấp vào nút Update
        self.btn_update_launcher.setEnabled(False)
        self.btn_update_launcher.setText("Đang tải bản cập nhật...")
        
        self.updater_worker = LauncherUpdaterWorker()
        self.updater_worker.status_signal.connect(lambda status: self.btn_update_launcher.setText(status))
        self.updater_worker.finished_signal.connect(self.on_update_finished)
        self.updater_worker.start()

    def on_update_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Cập nhật thành công", message)
            # Thoát ngay lập tức để file .bat (đã kích hoạt) làm nhiệm vụ ghi đè code
            self.close() 
        else:
            QMessageBox.critical(self, "Lỗi", message)
            self.btn_update_launcher.setEnabled(True)
            self.btn_update_launcher.setText("Thử cập nhật lại")