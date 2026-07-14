import json
import os
import subprocess
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QFontDatabase, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.game_manager import (
    get_all_games,
    get_install_path,
    get_storage_info,
    save_install_path,
)
from core.updater import LauncherUpdaterWorker, check_launcher_update
from ui.add_game_dialog import AddGameDialog
from ui.login import LoginWindow
from ui.setting import SettingsPage
from ui.show_game_detail import GameDetailPage
from ui.store_build import StorePage
from ui.widgets.game_card import GameCard

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):

    def __init__(self, username, is_admin, is_verified=False):
        super().__init__()
        # --- TẢI FONT CHỮ TÙY CHỈNH TỪ THƯ MỤC LÊN ---
        font_path = os.path.join(
            BASE_DIR, "assets", "fonts", "MontenegrinGothicOne-Regular.ttf"
        )
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)

        self.username = username

        # --- KIỂM TRA CHÉO TOÀN DIỆN QUYỀN ADMIN & VERIFIED ---
        # Đảm bảo dù session truyền vào là False thì vẫn tự đọc chuẩn từ DB
        self.is_admin, self.is_verified = self.check_user_privileges(
            username, is_admin, is_verified
        )

        self.games_data = get_all_games()  # Load data game từ JSON

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
        self.btn_update_launcher.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold;"
        )
        self.btn_update_launcher.hide()
        self.btn_update_launcher.clicked.connect(self.start_update_launcher)

        self.check_version()

        # Mặc định mở Launcher là chọn nút Store
        self.set_active_nav(self.btn_store)

    def check_user_privileges(
        self, username, current_admin, current_verified
    ):
        """
        Quét toàn diện các file JSON để tìm chính xác quyền Admin và trạng thái Verified.
        Xử lý mượt mà cả cấu trúc Dict {"user": {...}} lẫn List [{"username": "..."}].
        """
        is_admin_res = current_admin
        is_verified_res = current_verified

        # Nếu cả 2 đều đã là True từ phiên đăng nhập thì không cần đọc file nữa
        if is_admin_res and is_verified_res:
            return True, True

        # Danh sách tất cả đường dẫn khả nghi có thể chứa thông tin user
        possible_paths = [
            os.path.join(BASE_DIR, "users.json"),
            os.path.join(BASE_DIR, "config", "users.json"),  # Bổ sung config/
            os.path.join(BASE_DIR, "data", "users.json"),
            os.path.join(BASE_DIR, "core", "users.json"),
            os.path.join(BASE_DIR, "session.json"),  # Kiểm tra luôn file session
        ]

        truthy_values = [True, "true", "True", 1, "1", "yes", "Yes"]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        # TRƯỜNG HỢP 1: File JSON dạng Từ điển (Dict)
                        if isinstance(data, dict):
                            # Kiểm tra nếu key chính là username (VD: {"tand6381": {"is_verified": true}})
                            for key, val in data.items():
                                if (
                                    key.lower() == username.lower()
                                    and isinstance(val, dict)
                                ):
                                    if val.get("is_verified") in truthy_values:
                                        is_verified_res = True
                                    if val.get("is_admin") in truthy_values:
                                        is_admin_res = True

                            # Kiểm tra nếu dict lưu theo email/id, nhưng bên trong có trường username
                            for val in data.values():
                                if (
                                    isinstance(val, dict)
                                    and val.get("username", "").lower()
                                    == username.lower()
                                ):
                                    if val.get("is_verified") in truthy_values:
                                        is_verified_res = True
                                    if val.get("is_admin") in truthy_values:
                                        is_admin_res = True

                            # Trường hợp đọc file session.json (VD: {"username": "tand6381", "is_verified": true})
                            if (
                                data.get("username", "").lower()
                                == username.lower()
                            ):
                                if data.get("is_verified") in truthy_values:
                                    is_verified_res = True
                                if data.get("is_admin") in truthy_values:
                                    is_admin_res = True

                        # TRƯỜNG HỢP 2: File JSON dạng Danh sách (List)
                        elif isinstance(data, list):
                            for item in data:
                                if (
                                    isinstance(item, dict)
                                    and item.get("username", "").lower()
                                    == username.lower()
                                ):
                                    if item.get("is_verified") in truthy_values:
                                        is_verified_res = True
                                    if item.get("is_admin") in truthy_values:
                                        is_admin_res = True
                except Exception as e:
                    print(f"Lỗi đọc quyền từ file {path}: {e}")

        return is_admin_res, is_verified_res

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
            self.lbl_logo.setPixmap(
                pixmap.scaled(
                    200,
                    160,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.lbl_logo.setText("WM VANGROK")
            self.lbl_logo.setObjectName("logo_text")
            self.lbl_logo.setStyleSheet(
                "font-size: 26px; font-weight: bold; color: #ff4d4d; letter-spacing: 2px;"
            )

        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(self.lbl_logo)
        self.sidebar_layout.addSpacing(15)

        # --- NÚT STORE ---
        self.btn_store = self.create_nav_button("STORE")
        self.btn_store.clicked.connect(self.on_store_clicked)
        self.sidebar_layout.addWidget(self.btn_store)

        # --- NÚT LIBRARY ---
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

        # Nút sẽ sáng khi là Admin HOẶC đã Xác thực tài khoản
        self.btn_add_game.setVisible(self.is_admin or self.is_verified)

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

        self.build_library_page()  # Index 1: Library

        self.detail_page = GameDetailPage(base_dir=BASE_DIR, parent=self)
        self.detail_page.back_requested.connect(self.on_store_clicked)
        self.content_area.addWidget(self.detail_page)  # Index 2: Detail Game

        self.settings_page = SettingsPage(self)
        self.settings_page.set_current_username(self.username)
        self.settings_page.path_changed_signal.connect(self.update_storage_ui)
        self.settings_page.username_changed_signal.connect(
            self.update_ui_username
        )
        self.content_area.addWidget(self.settings_page)  # Index 3: Setting

        right_layout.addWidget(self.content_area)
        main_layout.addWidget(right_panel)

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
        self.games_data = get_all_games()
        self.refresh_sidebar_installed_games()
        self.set_active_nav(self.btn_store)
        self.content_area.setCurrentIndex(0)

    def on_library_clicked(self):
        self.games_data = get_all_games()
        self.refresh_sidebar_installed_games()
        self.refresh_library_page()
        self.set_active_nav(self.btn_library)
        self.content_area.setCurrentIndex(1)

    def on_setting_clicked(self):
        self.set_active_nav(self.btn_setting)
        self.settings_page.update_storage_ui()
        self.content_area.setCurrentIndex(3)

    def update_ui_username(self, new_name):
        self.username = new_name
        self.btn_user.setText(f"👤 {self.username.upper()}  ▼")
        # Quét lại quyền khi đổi tên hoặc khi có sự thay đổi từ trang Settings
        self.is_admin, self.is_verified = self.check_user_privileges(
            new_name, False, False
        )
        self.btn_add_game.setVisible(self.is_admin or self.is_verified)

    def get_installed_games(self):
        installed = []
        for g in self.games_data:
            game_id = g.get("id")
            exe_path = g.get("exe_path")

            if game_id and exe_path:
                game_dir = os.path.join(
                    BASE_DIR, "installed_games", str(game_id)
                )
                full_exe_path = os.path.join(game_dir, str(exe_path))

                if os.path.exists(full_exe_path):
                    installed.append(g)

        return installed

    def refresh_sidebar_installed_games(self):
        while self.installed_games_layout.count():
            item = self.installed_games_layout.takeAt(0)
            if item.widget():
                if item.widget() in self.nav_buttons:
                    self.nav_buttons.remove(item.widget())
                item.widget().deleteLater()

        installed_games = self.get_installed_games()

        if not installed_games:
            lbl_empty = QLabel("Chưa cài game nào")
            lbl_empty.setStyleSheet(
                "color: #666666; font-size: 13px; font-style: italic; padding-left: 15px;"
            )
            self.installed_games_layout.addWidget(lbl_empty)
        else:
            for game in installed_games:
                btn_game = self.create_nav_button(f"▪ {game['name']}")
                btn_game.setStyleSheet(
                    "padding-left: 25px; font-size: 14px; font-weight: normal;"
                )
                btn_game.clicked.connect(
                    lambda checked, g=game, b=btn_game: self.on_sidebar_game_clicked(
                        g, b
                    )
                )
                self.installed_games_layout.addWidget(btn_game)

    def on_sidebar_game_clicked(self, game_data, btn_clicked):
        self.set_active_nav(btn_clicked)
        self.show_game_detail(game_data)

    def build_library_page(self):
        self.library_page = QWidget()
        self.library_layout = QVBoxLayout(self.library_page)
        self.library_layout.setContentsMargins(30, 20, 30, 20)

        lbl_title = QLabel("MY LIBRARY")
        lbl_title.setStyleSheet(
            "font-size: 40px; font-weight: bold; color: white; letter-spacing: 1px;"
        )
        self.library_layout.addWidget(lbl_title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(
            "border-top: 2px solid #ff4d4d; margin-bottom: 20px;"
        )
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

        installed_games = self.get_installed_games()

        if not installed_games:
            lbl_empty_lib = QLabel(
                "Bạn chưa tải trò chơi nào.\nHãy sang mục Store để khám phá và cài đặt game"
            )
            lbl_empty_lib.setStyleSheet(
                "color: #aaaaaa; font-size: 18px; line-height: 1.5;"
            )
            lbl_empty_lib.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.library_grid_layout.addWidget(lbl_empty_lib)
        else:
            for game in installed_games:
                card = GameCard(game)
                card.card_clicked.connect(self.show_game_detail)
                self.library_grid_layout.addWidget(card)
            self.library_grid_layout.addStretch()

    def show_game_detail(self, game_data):
        self.detail_page.set_game_data(game_data)
        self.content_area.setCurrentIndex(2)

    def update_storage_ui(self):
        current_path = get_install_path()
        total_gb, used_gb, free_gb = get_storage_info(current_path)

        drive_name = os.path.splitdrive(current_path)[0]
        if not drive_name:
            drive_name = "Disk"

        self.store_page.update_storage(drive_name, free_gb, total_gb, used_gb)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-family: 'Montenegrin Gothic One',
                             'MontenegrinGothicOne-Regular',
                             'Orbitron',
                             'Rajdhani',
                             'Segoe UI',
                             sans-serif;
            }

            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #424242,
                    stop:1 #4a4a4a
                );
            }

            #sidebar {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:0,
                    stop:0 #242424,
                    stop:1 #2d2d2d
                );
                border-right: 1px solid #ff4d4d;
            }

            #right_panel {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #474747,
                    stop:1 #4a4a4a
                );
            }

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
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:0,
                    stop:0 #383838,
                    stop:1 #444444
                );
                color: #ffffff;
            }

            QPushButton[nav_btn="true"][active="true"] {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:0,
                    stop:0 #404040,
                    stop:1 #4d4d4d
                );
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
                background-color: transparent;
                border: 1px solid #ff4d4d;
                color: #ff4d4d;
                border-radius: 5px;
                padding: 5px 15px;
                text-align: center;
                font-size: 13px;
                font-weight: bold;
            }

            #btn_admin:hover {
                background-color: #ff4d4d;
                color: white;
            }

            #storage_frame {
                border: 1px solid #ff4d4d;
                border-radius: 5px;

                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #2f2f2f,
                    stop:1 #393939
                );

                padding: 10px;
                min-width: 130px;
            }

            #storage_progress {
                border: none;
                background-color: #222222;
                border-radius: 5px;
            }

            #storage_progress::chunk {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:1, y2:0,
                    stop:0 #ff4d4d,
                    stop:1 #ff7777
                );
                border-radius: 5px;
            }

            #game_card {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #2c2c2c,
                    stop:1 #252525
                );

                border-radius: 8px;
                border: 1px solid transparent;
            }

            #game_card:hover {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #383838,
                    stop:1 #2d2d2d
                );

                border: 1px solid #ff4d4d;
            }

            #btn_action {
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                text-align: center;
                margin: 0px 5px 5px 5px;
            }

            #search_bar {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #303030,
                    stop:1 #242424
                );

                color: white;
                border: 1px solid #444444;
                border-radius: 10px;
                padding: 5px 15px;
                font-size: 14px;
                margin-bottom: 10px;
            }

            #search_bar:focus {
                border: 1px solid #ff4d4d;
            }

            #btn_win_ctrl,
            #btn_win_close {
                background-color: transparent;
                color: #aaaaaa;
                border: none;
                padding: 5px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                border-radius: 0px;
                min-width: 35px;
                max-height: 30px;
            }

            #btn_win_ctrl:hover {
                background-color: #555555;
                color: white;
            }

            #btn_win_close:hover {
                background-color: #e81123;
                color: white;
            }

            #btn_user {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #303030,
                    stop:1 #242424
                );

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
                border: 1px solid #ff4d4d;
                background-color: #383838;
            }

            #btn_user::menu-indicator {
                image: none;
            }

            QMenu {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #2b2b2b,
                    stop:1 #222222
                );

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

    def change_account(self):
        self.logout_requested = True
        self.close()

    def log_out(self):
        reply = QMessageBox.question(
            self,
            "Đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
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

    def open_add_game_dialog(self):
        dialog = AddGameDialog(self)
        dialog.exec()

    def check_version(self):
        needs_update, new_version = check_launcher_update()
        if needs_update:
            self.btn_update_launcher.setText(
                f"Có bản mới (v{new_version}) - Cập nhật ngay!"
            )
            self.btn_update_launcher.show()

    def start_update_launcher(self):
        self.btn_update_launcher.setEnabled(False)
        self.btn_update_launcher.setText("Đang tải bản cập nhật...")
        self.updater_worker = LauncherUpdaterWorker()
        self.updater_worker.status_signal.connect(
            lambda status: self.btn_update_launcher.setText(status)
        )
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