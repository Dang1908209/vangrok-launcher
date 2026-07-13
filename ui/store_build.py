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
            #storage_frame {
                border: 1px solid #ff4d4d; 
                border-radius: 5px; 
                background-color: #2b2b2b;
                padding: 10px; 
                min-width: 150px;
            }
            #storage_progress { border: none; background-color: #383838; border-radius: 5px; }
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
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # --- HEADER ROW (Title & Storage) ---
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        lbl_store = QLabel("STORE")
        lbl_store.setStyleSheet("font-size: 56px; font-weight: bold; color: white; letter-spacing: 2px;")
        lbl_desc = QLabel("Explore and install all available games")
        lbl_desc.setStyleSheet("font-size: 18px; color: #aaaaaa;")
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; max-width: 200px; margin-top: 5px; margin-bottom: 5px;")
        
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
        self.lbl_storage.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        
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
        # Tăng chiều cao một chút để có chỗ cho đồng hồ
        calendar_frame.setFixedHeight(270) 
        cal_frame_layout = QVBoxLayout(calendar_frame)
        cal_frame_layout.setContentsMargins(5, 10, 5, 5)
        
        # -- ĐỒNG HỒ VÀ NGÀY THÁNG --
        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clock.setStyleSheet("font-size: 26px; font-weight: bold; color: #ff4d4d; font-family: 'Orbitron', sans-serif; letter-spacing: 2px;")
        
        self.lbl_date = QLabel("Ngày / Tháng / Năm")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setStyleSheet("font-size: 13px; color: #aaaaaa; margin-bottom: 5px; font-weight: bold;")
        
        cal_frame_layout.addWidget(self.lbl_clock)
        cal_frame_layout.addWidget(self.lbl_date)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        # Làm gọn giao diện lịch bằng cách rút ngắn tên thứ tự và ẩn số tuần
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
        lbl_info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4d4d; letter-spacing: 1px;")
        
        lbl_info_content = QLabel(
            "• Chào mừng bạn đến với Launcher chính thức của Vangrok!\n"
            "• Luôn cập nhật phiên bản mới nhất từ trang chủ để tránh lỗi mismatch client.\n"
            "• Chúc các bạn có những trải nghiệm chơi game tuyệt vời nhất cùng bạn bè."
        )
        lbl_info_content.setStyleSheet("font-size: 14px; color: #dddddd; line-height: 1.6;")
        lbl_info_content.setWordWrap(True)
        lbl_info_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        info_frame_layout.addWidget(lbl_info_title)
        info_frame_layout.addWidget(lbl_info_content)
        info_frame_layout.addStretch()
        
        # -- HIỂN THỊ VERSION LAUNCHER --
        lbl_version = QLabel("Vangrok Launcher v1.0.0")
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_version.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
        info_frame_layout.addWidget(lbl_version)
        
        # Chia tỉ lệ Layout: Lịch chiếm 4 phần, Bảng thông báo chiếm 5 phần chiều ngang
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
        
        # --- Banner ---
        banner = QFrame()
        banner.setObjectName("banner")
        banner.setFixedHeight(140)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 20, 20, 20)
        
        banner_title = self.games_data[0]["name"] if self.games_data else "Game"
        banner_ver = self.games_data[0]["version"] if self.games_data else "x.x.x"
        banner_size = f"{self.games_data[0]['size']} GB" if self.games_data else "N/A GB"
        
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
        
        lbl_banner_size = QLabel(str(banner_size))
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
            lbl_empty.setStyleSheet("color: #aaaaaa; font-size: 16px; font-style: italic;")
            self.cards_layout.addWidget(lbl_empty)
            
        self.cards_layout.addStretch()

    def update_storage(self, drive_name, free_gb, total_gb, used_gb):
        """Hàm công khai để MainWindow có thể gọi và cập nhật thông số ổ đĩa"""
        self.lbl_storage.setText(f"Drive {drive_name}\n{free_gb} GB free")
        self.progress_storage.setMaximum(total_gb)
        self.progress_storage.setValue(used_gb)