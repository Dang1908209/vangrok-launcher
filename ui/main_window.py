import json
import os
import subprocess
from PyQt6.QtCore import QPoint, Qt, QDateTime
from PyQt6.QtGui import QAction, QFontDatabase, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
from core.discord_rpc import DiscordRPCWorker  # --- [NEW] Import luồng Discord RPC ---
from ui.add_game_dialog import AddGameDialog
from ui.login import LoginWindow
from ui.news_dialog import NewsDialog
from ui.setting import SettingsPage, TranslatorWorker
from ui.show_game_detail import GameDetailPage
from ui.store_build import StorePage
from ui.widgets.game_card import GameCard
from ui.dev_stats import DevStatsPage

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- HỆ THỐNG QUẢN LÝ CHỈ SỐ THƯ VIỆN GAME THỦ ---
STATS_FILE = os.path.join(BASE_DIR, "config", "library_stats.json")


def load_library_stats():
    """Tải thông số giờ chơi và yêu thích từ file JSON cục bộ"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_library_stats(stats):
    """Lưu thông số giờ chơi và yêu thích"""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Không thể lưu stats: {e}")


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
        self.is_admin, self.is_verified = self.check_user_privileges(
            username, is_admin, is_verified
        )

        self.games_data = get_all_games()

        self.setWindowTitle("Vangrok Launcher")
        self.resize(1100, 650)

        # 1. Ẩn thanh tiêu đề mặc định của Windows
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.old_pos = None

        self.nav_buttons = []
        self.translator_worker = None  # Khởi tạo biến quản lý luồng dịch

        self.setup_ui()
        self.apply_styles()

        # Kiểm tra cập nhật ngay sau khi vẽ UI xong
        self.check_version()

        # Mặc định mở Launcher là chọn nút Store
        if hasattr(self, "btn_store"):
            self.set_active_nav(self.btn_store)
        
        # --- [NEW] Khởi chạy luồng Discord RPC & Cập nhật trạng thái ban đầu ---
        self.discord_worker = DiscordRPCWorker(client_id="1526826608823111750")
        self.discord_worker.start()
        self.discord_worker.update_status("Đang lướt Cửa hàng", "Khám phá game mới")

    # ================= KHỐI HÀM DỊCH TOÀN BỘ APP =================
    def translate_whole_app(self, target_lang):
        if hasattr(self.settings_page, "cbx_language"):
            self.settings_page.cbx_language.setEnabled(False)
            self.settings_page.cbx_language.setToolTip("Đang dịch toàn bộ hệ thống...")

        texts_to_translate = []
        for widget in self.findChildren((QLabel, QPushButton, QCheckBox, QAction)):
            if hasattr(self.settings_page, "cbx_language") and widget == self.settings_page.cbx_language:
                continue
            if not hasattr(widget, "text"):
                continue
            current_text = widget.text().strip()
            if not current_text or widget.property("is_dynamic"):
                continue

            orig_text = widget.property("orig_text")
            if not orig_text:
                orig_text = current_text
                widget.setProperty("orig_text", orig_text)

            if orig_text not in texts_to_translate:
                texts_to_translate.append(orig_text)

        self.translator_worker = TranslatorWorker(texts_to_translate, target_lang)
        self.translator_worker.finished_signal.connect(self.apply_global_translation)
        self.translator_worker.start()

    def on_dev_stats_clicked(self):
        self.dev_stats_page.update_data(self.games_data)
        self.content_area.setCurrentIndex(4)

    def refresh_dev_stats_data(self):
        if hasattr(self, "load_games_data"):
            self.load_games_data()
        elif hasattr(self, "reload_database"):
            self.reload_database()
            
        self.dev_stats_page.update_data(self.games_data)

    def apply_global_translation(self, translated_map, target_lang):
        for widget in self.findChildren((QLabel, QPushButton, QCheckBox, QAction)):
            if hasattr(self.settings_page, "cbx_language") and widget == self.settings_page.cbx_language:
                continue
            orig_text = widget.property("orig_text")
            if orig_text:
                if target_lang == "vi":
                    widget.setText(orig_text)
                elif orig_text in translated_map:
                    widget.setText(translated_map[orig_text])

        if hasattr(self.settings_page, "cbx_language"):
            self.settings_page.cbx_language.setEnabled(True)
            self.settings_page.cbx_language.setToolTip("")

        if not translated_map and target_lang != "vi":
            QMessageBox.warning(
                self,
                "Thiếu Thư Viện",
                "Bạn cần chạy lệnh:\npip install deep-translator\nđể bật tính năng dịch tự động Google Translate!",
            )

    def check_user_privileges(self, username, current_admin, current_verified):
        is_admin_res = current_admin
        is_verified_res = current_verified

        if is_admin_res and is_verified_res:
            return True, True

        possible_paths = [
            os.path.join(BASE_DIR, "users.json"),
            os.path.join(BASE_DIR, "config", "users.json"),
            os.path.join(BASE_DIR, "data", "users.json"),
            os.path.join(BASE_DIR, "core", "users.json"),
            os.path.join(BASE_DIR, "session.json"),
        ]

        truthy_values = [True, "true", "True", 1, "1", "yes", "Yes"]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                        if isinstance(data, dict):
                            for key, val in data.items():
                                if key.lower() == username.lower() and isinstance(val, dict):
                                    if val.get("is_verified") in truthy_values:
                                        is_verified_res = True
                                    if val.get("is_admin") in truthy_values:
                                        is_admin_res = True

                            for val in data.values():
                                if isinstance(val, dict) and val.get("username", "").lower() == username.lower():
                                    if val.get("is_verified") in truthy_values:
                                        is_verified_res = True
                                    if val.get("is_admin") in truthy_values:
                                        is_admin_res = True

                            if data.get("username", "").lower() == username.lower():
                                if data.get("is_verified") in truthy_values:
                                    is_verified_res = True
                                if data.get("is_admin") in truthy_values:
                                    is_admin_res = True

                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and item.get("username", "").lower() == username.lower():
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
        self.lbl_logo.setProperty("is_dynamic", True)
        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.lbl_logo.setPixmap(
                pixmap.scaled(200, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        if hasattr(self, "create_nav_button"):
            self.btn_store = self.create_nav_button("STORE")
            self.btn_store.clicked.connect(self.on_store_clicked)
            self.sidebar_layout.addWidget(self.btn_store)

            # --- NÚT LIBRARY ---
            self.btn_library = self.create_nav_button("LIBRARY")
            self.btn_library.clicked.connect(self.on_library_clicked)
            self.sidebar_layout.addWidget(self.btn_library)

            # --- NÚT NEWS ---
            self.btn_news = self.create_nav_button("📢 NEWS")
            if hasattr(self, "show_news"):
                self.btn_news.clicked.connect(self.show_news)
            self.sidebar_layout.addWidget(self.btn_news)

        self.sidebar_layout.addSpacing(15)

        lbl_library_header = QLabel("INSTALLED GAMES")
        lbl_library_header.setObjectName("library_title")
        self.sidebar_layout.addWidget(lbl_library_header)

        self.installed_games_layout = QVBoxLayout()
        self.sidebar_layout.addLayout(self.installed_games_layout)
        if hasattr(self, "refresh_sidebar_installed_games"):
            self.refresh_sidebar_installed_games()

        self.sidebar_layout.addStretch()

        # --- NÚT SETTINGS ---
        if hasattr(self, "create_nav_button"):
            self.btn_setting = self.create_nav_button("⚙ Setting")
            if hasattr(self, "on_setting_clicked"):
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

        # --- NÚT CẬP NHẬT LAUNCHER ---
        self.btn_update_launcher = QPushButton("Cập nhật Launcher!", self)
        self.btn_update_launcher.setProperty("is_dynamic", True)
        self.btn_update_launcher.setStyleSheet(
            "background-color: #e74c3c; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px;"
        )
        self.btn_update_launcher.hide()
        self.btn_update_launcher.clicked.connect(self.start_update_launcher)
        top_layout.addWidget(self.btn_update_launcher)

        # --- [QUAN TRỌNG] BẮT BUỘC PHẢI ADD VÀO LAYOUT THÌ MỚI HIỆN LÊN ĐƯỢC ---
        right_layout.addWidget(top_bar)
        
        # (Nếu bạn có self.content_area chứa Store, Library thì add tiếp ở dưới dòng này:)
        # right_layout.addWidget(self.content_area) 

        # Đưa toàn bộ khung bên phải vào layout chính của App
        main_layout.addWidget(right_panel)

        # --- NÚT THÊM GAME (ADMIN/VERIFIED) ---
        self.btn_add_game = QPushButton("+ Thêm trò chơi")
        self.btn_add_game.setObjectName("btn_admin")
        self.btn_add_game.setVisible(self.is_admin or self.is_verified)
        top_layout.addWidget(self.btn_add_game)
        self.btn_add_game.clicked.connect(self.open_add_game_dialog)

        # --- [MỚI] NÚT THỐNG KÊ DEVELOPER (ADMIN/VERIFIED) ---
        self.btn_dev_stats = QPushButton("📊 Thống kê Dev")
        self.btn_dev_stats.setObjectName("btn_admin")
        self.btn_dev_stats.setVisible(self.is_admin or self.is_verified)
        top_layout.addWidget(self.btn_dev_stats)
        self.btn_dev_stats.clicked.connect(self.on_dev_stats_clicked)

        # --- NÚT USER MENU ---
        self.btn_user = QPushButton(f"👤 {self.username.upper()} ▼")
        self.btn_user.setObjectName("btn_user")
        self.btn_user.setProperty("is_dynamic", True)  # Không dịch Username
        self.btn_user.setCursor(Qt.CursorShape.PointingHandCursor)

        user_menu = QMenu(self)
        user_menu.setObjectName("user_menu")

        action_change_acc = QAction("🔄 Change Account", self)
        action_change_acc.triggered.connect(self.change_account)

        action_logout = QAction("🚪 Log Out", self)
        action_logout.triggered.connect(self.log_out)

        user_menu.addAction(action_change_acc)
        user_menu.addSeparator()
        user_menu.addAction(action_logout)

        self.btn_user.setMenu(user_menu)
        top_layout.addWidget(self.btn_user)

        # --- CÁC NÚT ĐIỀU KHIỂN CỬA SỔ ---
        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("☐")
        self.btn_close = QPushButton("✕")

        self.btn_min.setProperty("is_dynamic", True)
        self.btn_max.setProperty("is_dynamic", True)
        self.btn_close.setProperty("is_dynamic", True)

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

        # KẾT NỐI TÍN HIỆU DỊCH TOÀN BỘ TẠI ĐÂY
        if hasattr(self.settings_page, "language_changed_signal"):
            self.settings_page.language_changed_signal.connect(
                self.translate_whole_app
            )

        self.content_area.addWidget(self.settings_page)  # Index 3: Setting

        # --- [MỚI] TRANG THỐNG KÊ DEVELOPER (Index 4) ---
        self.dev_stats_page = DevStatsPage(self.games_data, self)
        self.dev_stats_page.refresh_requested.connect(self.refresh_dev_stats_data)
        self.content_area.addWidget(self.dev_stats_page)  # Index 4: Dev Stats

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
        
        # --- [NEW] Cập nhật Discord RPC ---
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.update_status("Đang lướt Cửa hàng", "Khám phá game mới")

    def on_library_clicked(self):
        self.games_data = get_all_games()
        self.refresh_sidebar_installed_games()
        self.refresh_library_page()
        self.set_active_nav(self.btn_library)
        self.content_area.setCurrentIndex(1)
        
        # --- [NEW] Cập nhật Discord RPC ---
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.update_status("Đang xem Thư viện", "Chuẩn bị chiến game")

    def on_setting_clicked(self):
        self.set_active_nav(self.btn_setting)
        self.settings_page.update_storage_ui()
        self.content_area.setCurrentIndex(3)
        
        # --- [NEW] Cập nhật Discord RPC ---
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.update_status("Đang chỉnh sửa Cài đặt", "Tối ưu hóa Launcher")

    def update_storage_ui(self):
        """Hàm xử lý cập nhật giao diện lưu trữ khi nhận tín hiệu thay đổi đường dẫn"""
        if hasattr(self.settings_page, "update_storage_ui"):
            self.settings_page.update_storage_ui()

    def update_ui_username(self, new_name):
        self.username = new_name
        self.btn_user.setText(f"👤 {self.username.upper()} ▼")
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
                btn_game.setProperty("is_dynamic", True)
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

# =====================================================================
    # NÂNG CẤP BUILD_LIBRARY_PAGE - CHUẨN GIAO DIỆN STEAM DARK x VANGROK
    # =====================================================================
    def build_library_page(self):
        self.library_page = QWidget()
        self.library_page.setObjectName("LibraryPage")
        self.library_page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # CSS chuẩn Steam Dark pha chất Red Vangrok
        self.library_page.setStyleSheet("""
            #LibraryPage {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0.0 #1b2838,
                    stop: 0.4 #171a21,
                    stop: 1.0 #12141a
                );
            }
            
            /* Tiêu đề mục kệ game kiểu Steam */
            .ShelfHeader {
                color: #8f98a0;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1.5px;
            }
            
            /* Thanh tìm kiếm */
            #lib_search_bar {
                background-color: #25282e;
                border: 1px solid #3c404b;
                border-radius: 6px;
                padding: 6px 15px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            #lib_search_bar:focus {
                border: 1px solid #ff4d4d;
                background-color: #2c3038;
            }
            
            /* ComboBox bộ lọc */
            QComboBox {
                background-color: #25282e;
                border: 1px solid #3c404b;
                border-radius: 6px;
                padding: 5px 15px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                min-width: 140px;
            }
            QComboBox:hover {
                background-color: #2c3038;
                border: 1px solid #ff4d4d;
            }
            QComboBox QAbstractItemView {
                background-color: #171a21;
                color: #ffffff;
                border: 1px solid #ff4d4d;
                selection-background-color: #ff4d4d;
                selection-color: #ffffff;
            }
            
            /* ScrollArea trơn mượt */
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #12141a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3c404b;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #ff4d4d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
            }
        """)

        self.library_layout = QVBoxLayout(self.library_page)
        self.library_layout.setContentsMargins(30, 25, 30, 20)
        self.library_layout.setSpacing(20)

        # --- HEADER THƯ VIỆN ---
        header_layout = QHBoxLayout()
        lbl_title = QLabel("MY LIBRARY")
        lbl_title.setStyleSheet("font-size: 32px; font-weight: 900; color: #ffffff; letter-spacing: 2px; background: transparent;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.library_layout.addLayout(header_layout)

        # --- THANH CÔNG CỤ ĐIỀU KHIỂN (CONTROL BAR) ---
        control_bar = QFrame()
        control_bar.setStyleSheet("background-color: rgba(0, 0, 0, 0.2); border-radius: 8px; padding: 5px;")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(10, 8, 10, 8)
        control_layout.setSpacing(15)

        lbl_filter_icon = QLabel("⚡ FILTER BY:")
        lbl_filter_icon.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 12px; letter-spacing: 1px; background: transparent;")
        control_layout.addWidget(lbl_filter_icon)

        self.lib_filter_cb = QComboBox()
        self.lib_filter_cb.addItems(["Tất cả game", "Đã cài đặt", "Yêu thích ⭐"])
        self.lib_filter_cb.currentIndexChanged.connect(lambda: self.refresh_library_page())
        control_layout.addWidget(self.lib_filter_cb)

        self.lib_sort_cb = QComboBox()
        self.lib_sort_cb.addItems(["Sắp xếp: Tên A-Z", "Giờ chơi nhiều nhất", "Chơi gần đây"])
        self.lib_sort_cb.currentIndexChanged.connect(lambda: self.refresh_library_page())
        control_layout.addWidget(self.lib_sort_cb)

        control_layout.addStretch()

        self.lib_search_bar = QLineEdit()
        self.lib_search_bar.setPlaceholderText("🔍 Tìm trong thư viện...")
        self.lib_search_bar.setFixedWidth(250)
        self.lib_search_bar.setObjectName("lib_search_bar")
        self.lib_search_bar.textChanged.connect(lambda: self.refresh_library_page())
        control_layout.addWidget(self.lib_search_bar)

        self.library_layout.addWidget(control_bar)

        # --- VÙNG HIỂN THỊ KỆ GAME (SHELVES SCROLL AREA) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.shelves_container = QWidget()
        self.shelves_container.setStyleSheet("background: transparent;")
        
        # Bố cục dọc chính để chứa các "Kệ" (Shelves) như Steam
        self.shelves_layout = QVBoxLayout(self.shelves_container)
        self.shelves_layout.setContentsMargins(0, 10, 0, 20)
        self.shelves_layout.setSpacing(30)
        self.shelves_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Khóa dính phía trên cùng
        
        self.scroll_area.setWidget(self.shelves_container)
        self.library_layout.addWidget(self.scroll_area)

        self.content_area.addWidget(self.library_page)



    def check_version(self):
        print("[DEBUG] Đang bắt đầu kiểm tra phiên bản mới...")
        needs_update, new_version = check_launcher_update()
        print(f"[DEBUG] Kết quả check update: needs_update={needs_update}, version={new_version}")
        
        if needs_update:
            self.btn_update_launcher.setText(
                f"🚀 Có bản mới (v{new_version}) - Cập nhật ngay!"
            )
            self.btn_update_launcher.show()
            print("[DEBUG] Đã ra lệnh hiển thị nút Update!")
        else:
            print("[DEBUG] Không phát hiện bản update nào lớn hơn bản hiện tại.")

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

    # =====================================================================
    # NÂNG CẤP REFRESH_LIBRARY_PAGE - HỆ THỐNG KỆ (STEAM SHELVES)
    # =====================================================================
    def refresh_library_page(self):
        # Dọn dẹp sạch sẽ các kệ game cũ
        while self.shelves_layout.count():
            item = self.shelves_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        installed_games = self.get_installed_games() or []
        stats = load_library_stats()

        # Tạo thông số khởi tạo an toàn (Đã fix hoàn toàn lỗi TypeError float)
        is_dirty = False
        for game in installed_games:
            game_id = str(game.get("id", game.get("name")))
            if game_id not in stats:
                try:
                    num_id = int(game.get("id", 1))
                except (ValueError, TypeError):
                    num_id = abs(hash(game_id)) % 50 + 1

                stats[game_id] = {
                    "playtime_hours": round(num_id * 4.2 + 2.5, 1),
                    "last_played": QDateTime.currentDateTime().addDays(-int(num_id % 30)).toString("dd/MM/yyyy HH:mm"),
                    "is_favorite": False
                }
                is_dirty = True
        if is_dirty:
            save_library_stats(stats)

        search_query = self.lib_search_bar.text().lower().strip()
        filter_mode = self.lib_filter_cb.currentText()
        sort_mode = self.lib_sort_cb.currentText()

        # Lọc danh sách game
        filtered_library = []
        for game in installed_games:
            game_id = str(game.get("id", game.get("name")))
            game_stats = stats.get(game_id, {"playtime_hours": 0.0, "last_played": "Chưa chơi", "is_favorite": False})
            
            if search_query and search_query not in game.get("name", "").lower():
                continue
            if filter_mode == "Yêu thích ⭐" and not game_stats.get("is_favorite", False):
                continue

            filtered_library.append((game, game_stats))

        # Sắp xếp danh sách game
        if sort_mode == "Sắp xếp: Tên A-Z":
            filtered_library.sort(key=lambda x: x[0].get("name", "").lower())
        elif sort_mode == "Giờ chơi nhiều nhất":
            filtered_library.sort(key=lambda x: x[1].get("playtime_hours", 0.0), reverse=True)
        elif sort_mode == "Chơi gần đây":
            filtered_library.sort(key=lambda x: x[1].get("last_played", ""), reverse=True)

        # TRƯỜNG HỢP KHÔNG CÓ GAME: Hiển thị Empty State sang trọng
        if not filtered_library:
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addSpacing(50)
            
            lbl_empty = QLabel("🚫 KHÔNG TÌM THẤY TRÒ CHƠI NÀO TRONG THƯ VIỆN")
            lbl_empty.setStyleSheet("color: #67707b; font-size: 18px; font-weight: bold; letter-spacing: 1px;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl_sub = QLabel("Hãy khám phá Cửa hàng Vangrok và tải xuống những tựa game tuyệt đỉnh ngay hôm nay!")
            lbl_sub.setStyleSheet("color: #484f58; font-size: 14px; margin-top: 5px;")
            lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            empty_layout.addWidget(lbl_empty)
            empty_layout.addWidget(lbl_sub)
            self.shelves_layout.addWidget(empty_widget)
            return

        # ================= HÀM HỖ TRỢ VẼ KỆ GAME (SHELF BUILDER) =================
        def add_steam_shelf(title_text, games_list):
            if not games_list:
                return

            shelf_widget = QWidget()
            shelf_layout = QVBoxLayout(shelf_widget)
            shelf_layout.setContentsMargins(0, 0, 0, 0)
            shelf_layout.setSpacing(12)

            # Tiêu đề Kệ (Header + đường kẻ ngang Steam)
            header_box = QHBoxLayout()
            lbl_shelf_title = QLabel(f"{title_text} ({len(games_list)})")
            lbl_shelf_title.setProperty("class", "ShelfHeader")
            lbl_shelf_title.setStyleSheet("color: #67c1f5; font-size: 13px; font-weight: bold; letter-spacing: 1.5px;")
            header_box.addWidget(lbl_shelf_title)
            
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("border-top: 1px solid #283341; margin-top: 2px;")
            header_box.addWidget(line, 1) # Đường kẻ tự động kéo dài hết chiều ngang
            
            shelf_layout.addLayout(header_box)

            # Lưới Game (Grid)
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setSpacing(20)
            grid.setContentsMargins(0, 5, 0, 5)
            # Khóa góc trên trái: Thẻ game sẽ không bị văng ra giữa màn hình
            grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            max_columns = 4 # 4 game trên 1 hàng chuẩn desktop
            for idx, (g_data, g_info) in enumerate(games_list):
                row = idx // max_columns
                col = idx % max_columns
                
                card = GameCard(g_data)
                card.card_clicked.connect(self.show_game_detail)
                
                playtime_text = f"⏱️ {g_info.get('playtime_hours', 0)} hrs"
                card.setToolTip(f"🎮 {g_data.get('name')}\n{playtime_text}\nLần chơi cuối: {g_info.get('last_played')}")
                
                grid.addWidget(card, row, col)

            # Đẩy nhẹ cột cuối cùng bên phải để gom các game gọn gàng về bên trái
            grid.setColumnStretch(max_columns, 1)

            shelf_layout.addWidget(grid_widget)
            self.shelves_layout.addWidget(shelf_widget)

        # --- PHÂN LẠI KỆ GAME CHUẨN STEAM ---
        favorites_list = [item for item in filtered_library if item[1].get("is_favorite", False)]
        regular_list = [item for item in filtered_library if not item[1].get("is_favorite", False)]

        # Nếu đang ở chế độ lọc Tất Cả, hiển thị riêng Kệ Yêu Thích lên trên cùng (nếu có)
        if filter_mode == "Tất cả game" and favorites_list:
            add_steam_shelf("⭐ FAVORITES", favorites_list)
            add_steam_shelf("🎮 ALL GAMES", regular_list)
        else:
            # Nếu đang lọc riêng hoặc không có game yêu thích thì hiển thị 1 kệ chung
            title = "⭐ FAVORITE GAMES" if filter_mode == "Yêu thích ⭐" else "🎮 GAMES"
            add_steam_shelf(title, filtered_library)

        # Thêm lò xo dưới đáy để luôn đẩy toàn bộ kệ game lên sát bên trên
        self.shelves_layout.addStretch()

    def show_game_detail(self, game_data):
        self.detail_page.set_game_data(game_data)
        self.content_area.setCurrentIndex(2)
        
        # --- [NEW] Cập nhật Discord RPC khi xem chi tiết game ---
        game_name = game_data.get("name", "Một trò chơi")
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.update_status(f"Đang xem chi tiết: {game_name}", "Chuẩn bị tải / chơi game")

    def apply_styles(self):
        self.setStyleSheet(
            """
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
        """
        )

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
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and self.old_pos is not None
        ):
            self.move(event.globalPosition().toPoint() - self.old_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None
            event.accept()

    def open_add_game_dialog(self):
        dialog = AddGameDialog(self)
        dialog.exec()

    def show_news(self):
        # --- [NEW] Cập nhật RPC khi xem Tin tức ---
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.update_status("Đang đọc Tin tức", "Cập nhật thông báo mới")
            
        dialog = NewsDialog(self)
        dialog.exec()
        
        # --- [NEW] Sau khi đóng bảng tin tức, trả lại trạng thái trang trước đó ---
        if hasattr(self, "discord_worker") and self.discord_worker:
            current_idx = self.content_area.currentIndex()
            if current_idx == 0:
                self.discord_worker.update_status("Đang lướt Cửa hàng", "Khám phá game mới")
            elif current_idx == 1:
                self.discord_worker.update_status("Đang xem Thư viện", "Chuẩn bị chiến game")
            elif current_idx == 3:
                self.discord_worker.update_status("Đang chỉnh sửa Cài đặt", "Tối ưu hóa Launcher")

    def closeEvent(self, event):
        """--- [NEW] Xử lý đóng luồng Discord RPC an toàn khi thoát Launcher ---"""
        if hasattr(self, "discord_worker") and self.discord_worker:
            self.discord_worker.stop()
        super().closeEvent(event)