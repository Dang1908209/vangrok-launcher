import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QLineEdit, QPushButton,
                             QCalendarWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QDateTime
from PyQt6.QtGui import QFontDatabase
from ui.widgets.game_card import GameCard

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class StorePage(QWidget):
    # Tín hiệu phát ra kèm data của game khi người dùng click vào một GameCard
    game_detail_requested = pyqtSignal(dict)

    def __init__(self, games_data, parent=None):
        super().__init__(parent)
        self.games_data = games_data
        
        # --- BẮT BUỘC ĐỂ QWIDGET NHẬN MÀU NỀN TỪ STYLESHEET ---
        self.setObjectName("StorePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # -----------------------------------------------------

        self.load_fonts()
        self.setup_ui()

    def load_fonts(self):
        # Tự động quét và nạp toàn bộ font trong thư mục assets/fonts
        fonts_dir = os.path.join(BASE_DIR, "assets", "fonts")
        if os.path.exists(fonts_dir):
            for font_file in os.listdir(fonts_dir):
                if font_file.endswith(('.ttf', '.otf')):
                    QFontDatabase.addApplicationFont(os.path.join(fonts_dir, font_file))

    def get_launcher_version(self):
        """Đọc phiên bản Launcher từ file JSON cấu hình"""
        possible_paths = [
            os.path.join(BASE_DIR, "config", "version.json"),
            os.path.join(BASE_DIR, "config", "settings.json"),
            os.path.join(BASE_DIR, "version.json")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Hỗ trợ các key phổ biến thường dùng trong file config
                        version = data.get("version") or data.get("launcher_version") or data.get("app_version")
                        if version:
                            return f"Vangrok Launcher v{version}"
                except Exception:
                    pass
                
        # Giá trị mặc định nếu không đọc được từ JSON
        return "Vangrok Launcher v1.0.0"

    def setup_ui(self):
        # Cấu hình Style chung và tùy biến Lịch (QCalendarWidget) sang giao diện tối
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Montenegrin Gothic One', 'Orbitron', sans-serif; 
            }
            
            /* --- NỀN GRADIENT ĐEN - XÁM - ĐEN DỌC CHO TOÀN BỘ TRANG --- */
            QWidget#StorePage {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0.0 #111111,
                    stop: 0.5 #2d2d2d,
                    stop: 1.0 #111111
                );
            }
            
            #calendar_frame, #info_frame {
                background-color: #2b2b2b;
                border: 1px solid #ff4d4d;
                border-radius: 8px;
            }
            
            /* --- TÙY BIẾN GIAO DIỆN LỊCH (DARK & RED) --- */
            QCalendarWidget QWidget { 
                color: white; 
            }
            QCalendarWidget QNavigationButton {
                color: white;
                background-color: transparent;
            }
            QCalendarWidget QMenu { 
                background-color: #2b2b2b; 
                color: white; 
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: white;
                background-color: #2b2b2b;
                selection-background-color: #ff4d4d;
                selection-color: white;
            }
            QCalendarWidget QAbstractItemView:disabled { 
                color: #555555; 
            }
            
            /* --- STYLE CHO THANH SEARCH --- */
            #search_bar {
                background-color: #222222;
                border: 1px solid #555555;
                border-radius: 15px;
                padding: 5px 15px;
                color: white;
                font-weight: bold;
            }
            #search_bar:focus {
                border: 1px solid #ff4d4d;
                background-color: #2a2a2a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # --- HEADER ROW (Title) ---
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        lbl_store = QLabel("STORE")
        lbl_store.setStyleSheet("font-size: 56px; font-weight: bold; color: white; letter-spacing: 2px; background: transparent;")
        lbl_desc = QLabel("Explore and install all available games")
        lbl_desc.setStyleSheet("font-size: 18px; color: #aaaaaa; background: transparent;")
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; max-width: 200px; margin-top: 5px; margin-bottom: 5px; background: transparent;")
        
        title_layout.addWidget(lbl_store)
        title_layout.addWidget(line)
        title_layout.addWidget(lbl_desc)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # ================= DASHBOARD ZONE (CALENDAR & INFO) =================
        dashboard_layout = QHBoxLayout()
        dashboard_layout.setSpacing(20)
        
        # 1. Khung Lịch (Calendar Widget) & Thời gian
        calendar_frame = QFrame()
        calendar_frame.setObjectName("calendar_frame")
        calendar_frame.setFixedHeight(270) 
        cal_frame_layout = QVBoxLayout(calendar_frame)
        cal_frame_layout.setContentsMargins(5, 10, 5, 5)
        
        # -- ĐỒNG HỒ VÀ NGÀY THÁNG --
        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clock.setStyleSheet("font-size: 26px; font-weight: bold; color: #ff4d4d; font-family: 'Orbitron', sans-serif; letter-spacing: 2px; background: transparent;")
        
        self.lbl_date = QLabel("Ngày / Tháng / Năm")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setStyleSheet("font-size: 13px; color: #aaaaaa; margin-bottom: 5px; font-weight: bold; background: transparent;")
        
        cal_frame_layout.addWidget(self.lbl_clock)
        cal_frame_layout.addWidget(self.lbl_date)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.SingleLetterDayNames)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        cal_frame_layout.addWidget(self.calendar)
        
        # 2. Khung Thông tin / Thông báo hệ thống (Info Widget)
        info_frame = QFrame()
        info_frame.setObjectName("info_frame")
        info_frame.setFixedHeight(270)
        info_frame_layout = QVBoxLayout(info_frame)
        info_frame_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_info_title = QLabel("📢 SYSTEM ANNOUNCEMENTS")
        lbl_info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4d4d; letter-spacing: 1px; background: transparent;")
        
        lbl_info_content = QLabel(
            "• Welcome to official launcher of Vangrok!\n"
            "• ⚠ Attention: Please always update the latest version to have the best experience!\n"
        )
        lbl_info_content.setStyleSheet("font-size: 14px; color: #dddddd; line-height: 1.6; background: transparent;")
        lbl_info_content.setWordWrap(True)
        lbl_info_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        info_frame_layout.addWidget(lbl_info_title)
        info_frame_layout.addWidget(lbl_info_content)
        info_frame_layout.addStretch()
        
        # -- HIỂN THỊ VERSION LAUNCHER TỪ JSON --
        version_text = self.get_launcher_version()
        lbl_version = QLabel(version_text)
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_version.setStyleSheet("color: #666666; font-size: 12px; font-style: italic; background: transparent;")
        info_frame_layout.addWidget(lbl_version)
        
        dashboard_layout.addWidget(calendar_frame, stretch=4)
        dashboard_layout.addWidget(info_frame, stretch=5)
        layout.addLayout(dashboard_layout)
        
        # --- Thanh tìm kiếm ---
        search_layout = QHBoxLayout()
        search_layout.addStretch()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 SEARCH")
        self.search_bar.setFixedWidth(200)
        self.search_bar.setObjectName("search_bar")
        self.search_bar.textChanged.connect(self.filter_games)
        
        search_layout.addWidget(self.search_bar)
        layout.addLayout(search_layout)
        
        # --- Grid Game Cards ---
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(20)
        layout.addLayout(self.cards_layout)
        layout.addStretch()
        
        # Gọi hàm lọc lần đầu tiên để load toàn bộ game
        self.filter_games("")
        
        # ================= SETUP TIMER CHO ĐỒNG HỒ =================
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000) # Cập nhật mỗi giây
        self.update_datetime() # Gọi ngay lúc khởi tạo để hiển thị lập tức

    def update_datetime(self):
        """Hàm cập nhật Giờ và Ngày tháng liên tục"""
        current_time = QDateTime.currentDateTime()
        self.lbl_clock.setText(current_time.toString("HH:mm:ss"))
        self.lbl_date.setText(current_time.toString("dddd, dd / MM / yyyy"))

    def filter_games(self, query):
        """Hàm lọc và hiển thị lại các GameCard dựa trên từ khóa."""
        print(f"[DEBUG Store] Tổng số game trong data hiện tại: {len(self.games_data)}")
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        query = query.lower().strip()
        has_results = False
        
        for game in self.games_data:
            if query in game.get("name", "").lower():
                card = GameCard(game)
                card.card_clicked.connect(self.game_detail_requested.emit)
                self.cards_layout.addWidget(card)
                has_results = True
                
        if not has_results:
            lbl_empty = QLabel("Không tìm thấy trò chơi nào phù hợp.")
            lbl_empty.setStyleSheet("color: #aaaaaa; font-size: 16px; font-style: italic; background: transparent;")
            self.cards_layout.addWidget(lbl_empty)
            
        self.cards_layout.addStretch()

    def update_storage(self, *args, **kwargs):
        """
        Hàm giữ lại để tương thích ngược. 
        Tránh lỗi crash app (AttributeError) nếu MainWindow vẫn gọi cập nhật ổ đĩa.
        """
        pass

    def update_games_data(self, new_games_data):
        """Hàm cập nhật danh sách game mới từ MainWindow và vẽ lại giao diện"""
        self.games_data = new_games_data
        self.filter_games(self.search_bar.text())
        print("[DEBUG Store] Đã cập nhật giao diện Store với dữ liệu mới!")