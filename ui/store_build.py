import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QLineEdit, QPushButton, QComboBox,
                             QCalendarWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer, QDateTime, QRectF
from PyQt6.QtGui import QFontDatabase, QPainter, QColor, QPen, QBrush
from ui.widgets.game_card import GameCard

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =====================================================================
# 1. BỘ LỊCH SỰ KIỆN CUSTOM (EVENTS CALENDAR)
# =====================================================================
class EventsCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Danh sách các sự kiện tương tác định sẵn (Key: QDate -> Value: (Tiêu đề, Loại, Mã màu neon))
        # Sử dụng QDate.currentDate() để các mốc sự kiện luôn tự động xoay quanh ngày hiện tại của hệ thống
        today = QDate.currentDate()
        self.events = {
            today: (
                "🔥 HÔM NAY: Bản cập nhật Toad Mountain Patch 1.0.1 chính thức cập bến! Trải nghiệm ngay những tính năng tối ưu hiệu năng tuyệt vời.",
                "UPDATE", 
                "#ff4d4d"
            ),
            today.addDays(2): (
                "⚡ SỰ KIỆN: Cuối tuần nhân đôi kinh nghiệm (X2 EXP) cho toàn bộ chiến binh tham gia máy chủ Vangrok!",
                "EVENT", 
                "#f1c40f"
            ),
            today.addDays(-3): (
                "🔧 BẢO TRÌ: Đã hoàn tất nâng cấp cơ sở dữ liệu và tối ưu hóa đường truyền cụm máy chủ khu vực Đông Nam Á.",
                "MAINTENANCE", 
                "#3498db"
            ),
            today.addDays(5): (
                "🛍️ ĐỢT SALE: Lễ hội giảm giá game Indie mùa hè chính thức bắt đầu! Giảm giá cực sâu lên tới 75% cho các tựa game tuyển chọn.",
                "SALE", 
                "#2ecc71"
            )
        }

    def paintCell(self, painter, rect, date):
        # Vẽ ô lịch mặc định trước
        super().paintCell(painter, rect, date)
        
        # Nếu ngày này có sự kiện, vẽ một chấm tròn Neon phát sáng phía dưới số ngày
        if date in self.events:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Lấy màu sự kiện
            event_color = QColor(self.events[date][2])
            painter.setBrush(QBrush(event_color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Tính toán vị trí chấm tròn nhỏ ở sát đáy cell
            dot_size = 5
            dot_x = rect.x() + (rect.width() - dot_size) // 2
            dot_y = rect.y() + rect.height() - dot_size - 4
            
            painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
            painter.restore()


# =====================================================================
# 2. TRANG CỬA HÀNG CHÍNH (STORE PAGE)
# =====================================================================
class StorePage(QWidget):
    # Tín hiệu phát ra kèm data của game khi người dùng click vào một GameCard
    game_detail_requested = pyqtSignal(dict)

    def __init__(self, games_data, parent=None):
        super().__init__(parent)
        self.games_data = games_data if isinstance(games_data, list) else []
        
        # --- BẮT BUỘC ĐỂ QWIDGET NHẬN MÀU NỀN TỪ STYLESHEET ---
        self.setObjectName("StorePage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.load_fonts()
        self.setup_ui()

    def load_fonts(self):
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
                        version = data.get("version") or data.get("launcher_version") or data.get("app_version")
                        if version:
                            return f"Vangrok Launcher v{version}"
                except Exception:
                    pass
                
        return "Vangrok Launcher v1.0.0"

    def setup_ui(self):
        # Cấu hình Style chung, tùy biến Lịch, và thiết kế các hộp chọn ComboBox kiểu Cyberpunk
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Montenegrin Gothic One', 'Orbitron', sans-serif; 
            }
            
            /* --- NỀN GRADIENT ĐEN - XÁM - ĐEN DỌC --- */
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
            
            /* --- STYLE CHO CÁC HỘP CHỌN BỘ LỌC (COMBO BOX CYBERPUNK) --- */
            QComboBox {
                background-color: #222222;
                border: 1px solid #ff4d4d;
                border-radius: 14px;
                padding: 4px 15px;
                color: white;
                font-weight: bold;
                min-width: 140px;
            }
            QComboBox:hover {
                background-color: #2b2b2b;
                border: 1px solid #ff6666;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #ff4d4d;
                selection-background-color: #ff4d4d;
                selection-color: #000000;
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
        
        # 1. Khung Lịch Sự Kiện Đã Được Nâng Cấp
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
        
        # Gọi class bộ lịch sự kiện custom mới tạo
        self.calendar = EventsCalendar()
        self.calendar.setGridVisible(False)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.SingleLetterDayNames)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.clicked.connect(self.on_date_selected) # Kết nối click để cập nhật thông báo
        cal_frame_layout.addWidget(self.calendar)
        
        # 2. Khung Thông tin / Thông báo hệ thống (Info Widget)
        info_frame = QFrame()
        info_frame.setObjectName("info_frame")
        info_frame.setFixedHeight(270)
        self.info_frame_layout = QVBoxLayout(info_frame)
        self.info_frame_layout.setContentsMargins(20, 15, 20, 15)
        
        self.lbl_info_title = QLabel("📢 SYSTEM ANNOUNCEMENTS")
        self.lbl_info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4d4d; letter-spacing: 1px; background: transparent;")
        
        # Lưu nội dung thông báo tĩnh làm mặc định
        self.default_announcement = (
            "• Welcome to official launcher of Vangrok!\n"
            "• ⚠ Attention: Please always update the latest version to have the best experience!\n\n"
            "💡 [Mẹo]: Hãy click vào các ngày có dấu chấm sáng trên Lịch bên cạnh để xem các sự kiện đặc biệt của hệ thống!"
        )
        
        self.lbl_info_content = QLabel(self.default_announcement)
        self.lbl_info_content.setStyleSheet("font-size: 14px; color: #dddddd; line-height: 1.6; background: transparent;")
        self.lbl_info_content.setWordWrap(True)
        self.lbl_info_content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.info_frame_layout.addWidget(self.lbl_info_title)
        self.info_frame_layout.addWidget(self.lbl_info_content)
        self.info_frame_layout.addStretch()
        
        # -- HIỂN THỊ VERSION LAUNCHER TỪ JSON --
        version_text = self.get_launcher_version()
        lbl_version = QLabel(version_text)
        lbl_version.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_version.setStyleSheet("color: #666666; font-size: 12px; font-style: italic; background: transparent;")
        self.info_frame_layout.addWidget(lbl_version)
        
        dashboard_layout.addWidget(calendar_frame, stretch=4)
        dashboard_layout.addWidget(info_frame, stretch=5)
        layout.addLayout(dashboard_layout)
        
        # ================= NEW: HỆ THỐNG BỘ LỌC ĐA NĂNG & SẮP XẾP =================
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)
        
        # Thêm nhãn trang trí
        lbl_filter_tag = QLabel("⚡ FILTERS:")
        lbl_filter_tag.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 13px; margin-right: 5px;")
        filter_layout.addWidget(lbl_filter_tag)

        # 1. Hộp lọc thể loại game
        self.cb_genre = QComboBox()
        self.cb_genre.addItems(["Tất cả thể loại", "Hành động", "RPG", "Indie", "Chiến thuật", "Casual"])
        self.cb_genre.currentIndexChanged.connect(lambda: self.filter_games())
        filter_layout.addWidget(self.cb_genre)

        # 2. Hộp lọc Trạng thái / Badge
        self.cb_status = QComboBox()
        self.cb_status.addItems(["Tất cả trạng thái", "Free-to-Play", "Mới ra mắt", "Yêu thích nhất"])
        self.cb_status.currentIndexChanged.connect(lambda: self.filter_games())
        filter_layout.addWidget(self.cb_status)

        # 3. Hộp sắp xếp trò chơi
        self.cb_sort = QComboBox()
        self.cb_sort.addItems(["Sắp xếp: Mặc định", "Tên: A-Z", "Dung lượng: Tăng dần", "Lượt tải: Giảm dần"])
        self.cb_sort.currentIndexChanged.connect(lambda: self.filter_games())
        filter_layout.addWidget(self.cb_sort)

        filter_layout.addStretch()
        
        # 4. Giữ lại thanh Search cũ ở góc phải
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 SEARCH GAME...")
        self.search_bar.setFixedWidth(200)
        self.search_bar.setObjectName("search_bar")
        self.search_bar.textChanged.connect(lambda: self.filter_games())
        filter_layout.addWidget(self.search_bar)
        
        layout.addLayout(filter_layout)
        
        # --- Grid Game Cards ---
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(20)
        layout.addLayout(self.cards_layout)
        layout.addStretch()
        
        # Gọi hàm lọc lần đầu tiên để load toàn bộ game
        self.filter_games()
        
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

    def on_date_selected(self, date):
        """Hàm xử lý khi người dùng chọn một ngày trên lịch"""
        if date in self.calendar.events:
            event_text, event_type, event_color = self.calendar.events[date]
            self.lbl_info_title.setText(f"📅 SỰ KIỆN HỆ THỐNG ({event_type})")
            self.lbl_info_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {event_color}; letter-spacing: 1px; background: transparent;")
            self.lbl_info_content.setText(f"Thông tin sự kiện ngày {date.toString('dd/MM/yyyy')}:\n\n{event_text}")
        else:
            # Nếu ngày không có sự kiện, quay về bảng thông báo mặc định ban đầu
            self.lbl_info_title.setText("📢 SYSTEM ANNOUNCEMENTS")
            self.lbl_info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff4d4d; letter-spacing: 1px; background: transparent;")
            self.lbl_info_content.setText(self.default_announcement)

    def filter_games(self, dummy_arg=None):
        """Hàm lọc nâng cao kết hợp Từ khóa tìm kiếm, Thể loại, Trạng thái và Sắp xếp."""
        # Giải phóng các Card cũ trên UI
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        query = self.search_bar.text().lower().strip()
        genre_filter = self.cb_genre.currentText()
        status_filter = self.cb_status.currentText()
        sort_mode = self.cb_sort.currentText()
        
        filtered_list = []
        
        # --- 1. TIẾN HÀNH LỌC ---
        for game in self.games_data:
            # Lọc theo từ khoá tìm kiếm
            if query and query not in game.get("name", "").lower():
                continue
            
            # Lọc theo Thể loại (Genre)
            if genre_filter != "Tất cả thể loại":
                game_genre = game.get("genre", "").lower()
                genre_map = {
                    "Hành động": "action",
                    "RPG": "rpg",
                    "Indie": "indie",
                    "Chiến thuật": "strategy",
                    "Casual": "casual"
                }
                target_genre = genre_map.get(genre_filter, "")
                if target_genre not in game_genre:
                    continue
                    
            # Lọc theo Trạng thái (Status / Tag của Game)
            if status_filter != "Tất cả trạng thái":
                # Gom nhóm mọi tag có thể có từ dữ liệu JSON của game
                game_tags = [str(t).lower() for t in game.get("tags", [])] + [
                    str(game.get("status", "")).lower(), 
                    str(game.get("tag", "")).lower()
                ]
                
                if status_filter == "Free-to-Play" and ("free" not in game_tags and "free-to-play" not in game_tags):
                    continue
                elif status_filter == "Mới ra mắt" and ("new" not in game_tags and "mới" not in game_tags):
                    continue
                elif status_filter == "Yêu thích nhất" and ("hot" not in game_tags and "bán chạy" not in game_tags):
                    continue
            
            filtered_list.append(game)
            
        # --- 2. TIẾN HÀNH SẮP XẾP (SORTING) ---
        if sort_mode == "Tên: A-Z":
            filtered_list.sort(key=lambda x: x.get("name", "").lower())
        elif sort_mode == "Dung lượng: Tăng dần":
            def parse_size(g):
                size_val = g.get("size_mb", g.get("size", g.get("file_size", 0)))
                try:
                    return float(size_val)
                except (ValueError, TypeError):
                    return 0.0
            filtered_list.sort(key=parse_size)
        elif sort_mode == "Lượt tải: Giảm dần":
            def parse_downloads(g):
                downloads_val = g.get("downloads", g.get("download_count", g.get("total_downloads", 0)))
                try:
                    return int(downloads_val)
                except (ValueError, TypeError):
                    return 0
            filtered_list.sort(key=parse_downloads, reverse=True)

        # --- 3. ĐẨY LÊN GIAO DIỆN ---
        has_results = len(filtered_list) > 0
        for game in filtered_list:
            card = GameCard(game)
            card.card_clicked.connect(self.game_detail_requested.emit)
            self.cards_layout.addWidget(card)
                
        if not has_results:
            lbl_empty = QLabel("Không tìm thấy trò chơi nào phù hợp với bộ lọc hiện tại.")
            lbl_empty.setStyleSheet("color: #aaaaaa; font-size: 16px; font-style: italic; background: transparent;")
            self.cards_layout.addWidget(lbl_empty)
            
        self.cards_layout.addStretch()

    def update_storage(self, *args, **kwargs):
        """Hàm tương thích ngược tránh lỗi crash app"""
        pass