import os
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QPushButton, QFrame, QStackedWidget, 
                             QLineEdit, QMessageBox, QFileDialog, QMenu)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QAction, QFontDatabase

from ui.add_game_dialog import AddGameDialog
from ui.widgets.game_card import GameCard
from ui.login import LoginWindow 
from ui.setting import SettingsPage
from ui.store_build import StorePage  # Import file giao diện Store vừa tách
from core.updater import check_launcher_update, LauncherUpdaterWorker
from core.game_manager import get_all_games, get_install_path, save_install_path, get_storage_info

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MainWindow(QMainWindow):
    def __init__(self, username, is_admin):
        super().__init__()
        # --- TẢI FONT CHỮ TÙY CHỈNH TỪ THƯ MỤC LÊN ---
        font_path = os.path.join(BASE_DIR, "assets", "fonts", "MontenegrinGothicOne-Regular.ttf")
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)
            
        self.username = username
        self.is_admin = is_admin
        self.games_data = get_all_games() # Load data game từ JSON
        
        self.setWindowTitle("Vangrok Launcher")
        self.resize(1100, 650)
        
        # 1. Ẩn thanh tiêu đề mặc định của Windows
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.old_pos = None
        
        # Danh sách quản lý các nút Navigation ở Sidebar để xử lý hiệu ứng Active
        self.nav_buttons = []
        
        self.setup_ui()
        self.apply_styles()
        
        # Cập nhật dung lượng thật của ổ đĩa ngay khi mở ứng dụng
        self.update_storage_ui()

        self.btn_update_launcher = QPushButton("Cập nhật Launcher!", self)
        self.btn_update_launcher.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_update_launcher.hide() 
        self.btn_update_launcher.clicked.connect(self.start_update_launcher)
        
        self.check_version()
        
        # Mặc định mở Launcher là chọn nút Store
        self.set_active_nav(self.btn_store)
        
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
        self.sidebar_layout = QVBoxLayout(sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        self.sidebar_layout.setSpacing(5)
        
        self.lbl_logo = QLabel()
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Tăng kích thước logo lên chiếm ~1/4 chiều cao navbar
            self.lbl_logo.setPixmap(pixmap.scaled(200, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.lbl_logo.setText("WM VANGROK")
            self.lbl_logo.setObjectName("logo_text")
            self.lbl_logo.setStyleSheet("font-size: 26px; font-weight: bold; color: #ff4d4d; letter-spacing: 2px;")
        
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(self.lbl_logo)
        self.sidebar_layout.addSpacing(15)
        
        # --- NÚT STORE (Xem tất cả game) ---
        self.btn_store = self.create_nav_button("STORE")
        self.btn_store.clicked.connect(self.on_store_clicked)
        self.sidebar_layout.addWidget(self.btn_store)
        
        # --- NÚT LIBRARY (Chỉ xem game đã tải/cài đặt) ---
        self.btn_library = self.create_nav_button("LIBRARY")
        self.btn_library.clicked.connect(self.on_library_clicked)
        self.sidebar_layout.addWidget(self.btn_library)
        
        lbl_library_header = QLabel("INSTALLED GAMES")
        lbl_library_header.setObjectName("library_title")
        self.sidebar_layout.addWidget(lbl_library_header)
        
        self.installed_games_layout = QVBoxLayout()
        self.sidebar_layout.addLayout(self.installed_games_layout)
        self.refresh_sidebar_installed_games()
        
        self.sidebar_layout.addStretch()
        
        # --- NÚT SETTINGS ---
        self.btn_setting = self.create_nav_button("⚙  Setting")
        self.btn_setting.clicked.connect(self.on_setting_clicked)
        self.sidebar_layout.addWidget(self.btn_setting)
        
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
        
        self.btn_user = QPushButton(f"👤 {self.username.upper()}  ▼")
        self.btn_user.setObjectName("btn_user")
        self.btn_user.setCursor(Qt.CursorShape.PointingHandCursor)
        
        user_menu = QMenu(self)
        user_menu.setObjectName("user_menu")
        
        action_change_acc = QAction("🔄  Change Account", self)
        action_change_acc.triggered.connect(self.change_account)
        
        action_logout = QAction("🚪  Log Out", self)
        action_logout.triggered.connect(self.log_out)
        
        user_menu.addAction(action_change_acc)
        user_menu.addSeparator() 
        user_menu.addAction(action_logout)
        
        self.btn_user.setMenu(user_menu)
        top_layout.addWidget(self.btn_user)
        
        # Nút điều khiển cửa sổ
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
        
        # ================= STACKED WIDGET (CÁC TRANG) =================
        self.content_area = QStackedWidget()
        
        self.store_page = StorePage(self.games_data, self)
        self.store_page.game_detail_requested.connect(self.show_game_detail)
        self.content_area.addWidget(self.store_page)  # Index 0: Store 
        
        self.build_library_page()     # Index 1: Library
        self.build_detail_page()      # Index 2: Detail Game
        
        # Gọi Class Setting Page và các kết nối Signal
        self.settings_page = SettingsPage(self)
        self.settings_page.set_current_username(self.username)
        self.settings_page.path_changed_signal.connect(self.update_storage_ui)
        self.settings_page.username_changed_signal.connect(self.update_ui_username)
        self.content_area.addWidget(self.settings_page) # Index 3: Setting
        
        right_layout.addWidget(self.content_area)
        main_layout.addWidget(right_panel)

    # --- HÀM TẠO VÀ XỬ LÝ NÚT NAVIGATION ĐỘNG ---
    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("nav_btn", "true")
        btn.setProperty("active", "false")
        self.nav_buttons.append(btn)
        return btn

    def set_active_nav(self, active_btn):
        for btn in self.nav_buttons:
            if btn == active_btn:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def on_store_clicked(self):
        self.set_active_nav(self.btn_store)
        self.content_area.setCurrentIndex(0)

    def on_library_clicked(self):
        self.set_active_nav(self.btn_library)
        self.refresh_library_page()
        self.content_area.setCurrentIndex(1)

    def on_setting_clicked(self):
        self.set_active_nav(self.btn_setting)
        self.settings_page.update_storage_ui()
        self.content_area.setCurrentIndex(3)

    def update_ui_username(self, new_name):
        self.username = new_name
        self.btn_user.setText(f"👤 {self.username.upper()}  ▼")

    # --- LỌC VÀ HIỂN THỊ CHỈ GAME ĐÃ TẢI Ở SIDEBAR ---
    def refresh_sidebar_installed_games(self):
        while self.installed_games_layout.count():
            item = self.installed_games_layout.takeAt(0)
            if item.widget():
                if item.widget() in self.nav_buttons:
                    self.nav_buttons.remove(item.widget())
                item.widget().deleteLater()
                
        installed_games = [g for g in self.games_data if g.get("status", "Install") in ["Play", "Update"]]
        
        if not installed_games:
            lbl_empty = QLabel("Chưa cài game nào")
            lbl_empty.setStyleSheet("color: #666666; font-size: 13px; font-style: italic; padding-left: 15px;")
            self.installed_games_layout.addWidget(lbl_empty)
        else:
            for game in installed_games:
                btn_game = self.create_nav_button(f"▪ {game['name']}")
                btn_game.setStyleSheet("padding-left: 25px; font-size: 14px; font-weight: normal;") 
                btn_game.clicked.connect(lambda checked, g=game, b=btn_game: self.on_sidebar_game_clicked(g, b))
                self.installed_games_layout.addWidget(btn_game)

    def on_sidebar_game_clicked(self, game_data, btn_clicked):
        self.set_active_nav(btn_clicked)
        self.show_game_detail(game_data)

    # --- HÀM XỬ LÝ TRANG LIBRARY ---
    def build_library_page(self):
        self.library_page = QWidget()
        self.library_layout = QVBoxLayout(self.library_page)
        self.library_layout.setContentsMargins(30, 20, 30, 20)
        
        lbl_title = QLabel("MY LIBRARY")
        lbl_title.setStyleSheet("font-size: 40px; font-weight: bold; color: white; letter-spacing: 1px;")
        self.library_layout.addWidget(lbl_title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; margin-bottom: 20px;")
        self.library_layout.addWidget(line)
        
        self.library_grid_layout = QHBoxLayout()
        self.library_grid_layout.setSpacing(20)
        self.library_layout.addLayout(self.library_grid_layout)
        self.library_layout.addStretch()
        
        self.content_area.addWidget(self.library_page)

    def refresh_library_page(self):
        while self.library_grid_layout.count():
            item = self.library_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        installed_games = [g for g in self.games_data if g.get("status", "Install") in ["Play", "Update"]]
        
        if not installed_games:
            lbl_empty_lib = QLabel("Bạn chưa tải trò chơi nào.\nHãy sang mục Store để khám phá và cài đặt game")
            lbl_empty_lib.setStyleSheet("color: #aaaaaa; font-size: 18px; line-height: 1.5;")
            lbl_empty_lib.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.library_grid_layout.addWidget(lbl_empty_lib)
        else:
            for game in installed_games:
                card = GameCard(game)
                card.card_clicked.connect(self.show_game_detail)
                self.library_grid_layout.addWidget(card)
            self.library_grid_layout.addStretch()

    # --- HÀM XỬ LÝ TRANG CHI TIẾT GAME ---
    def build_detail_page(self):
        self.detail_page = QWidget()
        layout = QVBoxLayout(self.detail_page)
        layout.setContentsMargins(30, 20, 30, 20)
        
        btn_back = QPushButton("⬅ Quay lại")
        btn_back.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; text-align: left; padding: 0px; margin-bottom: 15px;")
        btn_back.setFixedWidth(120)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.clicked.connect(self.on_store_clicked)
        layout.addWidget(btn_back)
        
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
            
        self.content_area.setCurrentIndex(2)

    # --- TÍNH TOÁN DUNG LƯỢNG Ổ ĐĨA ---
    def update_storage_ui(self):
        current_path = get_install_path()
        total_gb, used_gb, free_gb = get_storage_info(current_path)
        
        drive_name = os.path.splitdrive(current_path)[0]
        if not drive_name:
            drive_name = "Disk"
            
        self.store_page.update_storage(drive_name, free_gb, total_gb, used_gb)

    # --- HÀM CẤU HÌNH GIAO DIỆN VÀ CSS ĐỘNG ---
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Montenegrin Gothic One', 'MontenegrinGothicOne-Regular', 'Orbitron', 'Rajdhani', 'Segoe UI', sans-serif; 
            }
            
            QMainWindow { background-color: #3b3b3b; }
            #sidebar {
                background-color: #2b2b2b;
                border-right: 1px solid #ff4d4d;
            }
            #right_panel { background-color: #4a4a4a; }
            
            QPushButton[nav_btn="true"] {
                background-color: transparent; 
                color: #cccccc; 
                border: none;
                border-left: 3px solid transparent;
                padding: 12px 15px; 
                font-size: 18px;
                font-weight: 600;
                text-align: left;
                border-radius: 0px;
                letter-spacing: 1px;
            }
            QPushButton[nav_btn="true"]:hover { 
                background-color: #383838; 
                color: #ffffff; 
            }
            QPushButton[nav_btn="true"][active="true"] { 
                background-color: #444444; 
                color: #ff4d4d;            
                font-weight: bold;
                border-left: 3px solid #ff4d4d; 
            }
            
            #library_title { 
                color: #888888; 
                font-size: 14px; 
                font-weight: bold; 
                margin-top: 30px; 
                margin-bottom: 5px; 
                padding-left: 15px; 
                letter-spacing: 1.5px;
            }
            
            #btn_admin {
                background-color: transparent; border: 1px solid #ff4d4d; color: #ff4d4d;
                border-radius: 5px; padding: 5px 15px; text-align: center; font-size: 13px; font-weight: bold;
            }
            #btn_admin:hover { background-color: #ff4d4d; color: white; }
            
            #storage_frame {
                border: 1px solid #ff4d4d; border-radius: 5px; background-color: #3b3b3b;
                padding: 10px; min-width: 130px;
            }
            #storage_progress { border: none; background-color: #2b2b2b; border-radius: 5px; }
            #storage_progress::chunk { background-color: #3498db; border-radius: 5px; }
            
            #game_card { 
                background-color: #2b2b2b; border-radius: 8px; border: 1px solid transparent; 
            }
            #game_card:hover { 
                background-color: #383838; border: 1px solid #ff4d4d; 
            }
            
            #btn_action { border-radius: 5px; padding: 5px; font-size: 14px; text-align: center; margin: 0px 5px 5px 5px; }
            
            #search_bar {
                background-color: #2b2b2b; color: white; border: none;
                border-radius: 10px; padding: 5px 15px; font-size: 14px; margin-bottom: 10px;
            }

            #btn_win_ctrl, #btn_win_close {
                background-color: transparent; color: #aaaaaa; border: none;
                padding: 5px 12px; font-size: 14px; font-weight: bold;
                text-align: center; border-radius: 0px; min-width: 35px; max-height: 30px;
            }
            #btn_win_ctrl:hover { background-color: #555555; color: white; }
            #btn_win_close:hover { background-color: #e81123; color: white; }

            #btn_user {
                background-color: #2b2b2b; color: white; border: 1px solid #555555;
                border-radius: 15px; padding: 5px 15px; font-size: 13px;
                font-weight: bold; text-align: center; margin-right: 15px;
            }
            #btn_user:hover { background-color: #383838; border: 1px solid #ff4d4d; }
            #btn_user::menu-indicator { image: none; }

            QMenu {
                background-color: #2b2b2b; color: white; border: 1px solid #ff4d4d;
                border-radius: 8px; padding: 5px 0px;
            }
            QMenu::item { padding: 8px 25px 8px 15px; font-size: 13px; font-weight: bold; }
            QMenu::item:selected { background-color: #ff4d4d; color: white; }
            QMenu::separator { height: 1px; background-color: #444444; margin: 4px 0px; }
        """)

    def change_account(self):
        self.logout_requested = True
        self.close()

    def log_out(self):
        reply = QMessageBox.question(
            self, "Đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested = True
            self.close()
            self.login_win = LoginWindow()
            self.login_win.show()

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

    def open_add_game_dialog(self):
        dialog = AddGameDialog(self)
        dialog.exec()

    def check_version(self):
        needs_update, new_version = check_launcher_update()
        if needs_update:
            self.btn_update_launcher.setText(f"Có bản mới (v{new_version}) - Cập nhật ngay!")
            self.btn_update_launcher.show()

    def start_update_launcher(self):
        self.btn_update_launcher.setEnabled(False)
        self.btn_update_launcher.setText("Đang tải bản cập nhật...")
        self.updater_worker = LauncherUpdaterWorker()
        self.updater_worker.status_signal.connect(lambda status: self.btn_update_launcher.setText(status))
        self.updater_worker.finished_signal.connect(self.on_update_finished)
        self.updater_worker.start()

    def on_update_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Cập nhật thành công", message)
            self.close() 
        else:
            QMessageBox.critical(self, "Lỗi", message)
            self.btn_update_launcher.setEnabled(True)
            self.btn_update_launcher.setText("Thử cập nhật lại")