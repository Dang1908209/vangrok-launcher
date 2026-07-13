import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QProgressBar, QLineEdit, QPushButton,
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
        
        # --- BẮT BUỘC ĐỂ QWIDGET NHẬN MAU NỀN TỪ STYLESHEET ---
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
            
            #storage_frame {
                border: 1px solid #ff4d4d; 
                border-radius: 5px; 
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #424242,
                    stop:1 #4a4a4a
                );
                padding: 10px; 
                min-width: 150px;
            }
            
            #storage_progress { 
                border: none;
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #383838,
                    stop:1 #4a4a4a
                ); 
                border-radius: 5px; 
            }
            #storage_progress::chunk { background-color: #ff4d4d; border-radius: 5px; }
            
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
        
        # --- HEADER ROW (Title & Storage) ---
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
        
        # Khung hiển thị dung lượng ổ cứng
        storage_frame = QFrame()
        storage_frame.setObjectName("storage_frame")
        storage_layout = QVBoxLayout(storage_frame)
        
        self.lbl_storage = QLabel("Storage: Đang tính...\nfree")
        self.lbl_storage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_storage.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent;")
        
        self.progress_storage = QProgressBar()
        self.progress_storage.setTextVisible(False)
        self.progress_storage.setFixedHeight(10)
        self.progress_storage.setObjectName("storage_progress")
        
        storage_layout.addWidget(self.lbl_storage)
        storage_layout.addWidget(self.progress_storage)
        header_layout.addWidget(storage_frame)
        
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
            "• Chào mừng bạn đến với Launcher chính thức của Vangrok!\n"
            "• Lưu ý luôn cập nhật phiên bản mới nhất từ trang chủ để tránh lỗi mismatch client.\n"
        )
        lbl_info_content.setStyleSheet("font-size: 14px; color: #dddddd; line-height: 1.6; background: transparent;")
        lbl_info_content.setWordWrap(True)
        lbl_info_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        info_frame_layout.addWidget(lbl_info_title)
        info_frame_layout.addWidget(lbl_info_content)
        info_frame_layout.addStretch()
        
        # -- HIỂN THỊ VERSION LAUNCHER --
        lbl_version = QLabel("Vangrok Launcher v1.0.0")
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

    def update_storage(self, drive_name, free_gb, total_gb, used_gb):
        """Hàm công khai để MainWindow có thể gọi và cập nhật thông số ổ đĩa"""
        self.lbl_storage.setText(f"Drive {drive_name}\n{free_gb} GB free")
        self.progress_storage.setMaximum(total_gb)
        self.progress_storage.setValue(used_gb)