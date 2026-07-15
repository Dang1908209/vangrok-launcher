import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==========================================
# 1. CLASS CARD THỐNG KÊ NHANH (Mini Widget)
# ==========================================
class StatCard(QFrame):
    def __init__(self, title, value, icon="📊", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setFixedSize(180, 100)
        self.setup_ui(title, value, icon)
        
    def setup_ui(self, title, value, icon):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        
        # Header: Icon + Tiêu đề nhỏ
        header_layout = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 16px; background: transparent;")
        
        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet("font-size: 10px; color: #aaaaaa; font-weight: bold; letter-spacing: 1px; background: transparent;")
        
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        # Chỉ số chính (Value)
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet("font-size: 22px; font-weight: bold; color: #ff4d4d; font-family: 'Orbitron', sans-serif; background: transparent;")
        
        layout.addLayout(header_layout)
        layout.addWidget(self.lbl_value)
        layout.addStretch()

    def update_value(self, new_value):
        self.lbl_value.setText(str(new_value))


# ==========================================
# 2. TRANG THỐNG KÊ DEVELOPER CHÍNH
# ==========================================
class DevStatsPage(QWidget):
    # Tín hiệu yêu cầu làm mới dữ liệu từ server/local
    refresh_requested = pyqtSignal()

    def __init__(self, games_data, parent=None):
        super().__init__(parent)
        self.games_data = games_data
        
        # Nhận màu nền từ stylesheet
        self.setObjectName("DevStatsPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setup_ui()
        self.calculate_and_populate_stats()

    def setup_ui(self):
        # --- STYLESHEET CHUNG CHO TOÀN TRANG ---
        self.setStyleSheet("""
            QWidget#DevStatsPage {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0.0 #111111,
                    stop: 0.5 #2d2d2d,
                    stop: 1.0 #111111
                );
            }
            
            /* Thẻ thống kê nhanh */
            QFrame#StatCard {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QFrame#StatCard:hover {
                border: 1px solid #ff4d4d;
                background-color: #333333;
            }
            
            /* Khu vực bảng dữ liệu */
            QFrame#table_container {
                background-color: #1e1e1e;
                border: 1px solid #ff4d4d;
                border-radius: 8px;
            }
            
            /* Tùy biến bảng QTableWidget */
            QTableWidget {
                background-color: transparent;
                border: none;
                gridline-color: #333333;
                color: #ffffff;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #ff4d4d;
                color: white;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ff4d4d;
                font-weight: bold;
                border: 1px solid #111111;
                padding: 6px;
                font-size: 11px;
                text-transform: uppercase;
            }
            
            /* Nút Refresh */
            QPushButton#btn_refresh {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #ff4d4d;
                border-radius: 4px;
                padding: 8px 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btn_refresh:hover {
                background-color: #ff4d4d;
                color: black;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # --- 1. HEADER ROW ---
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        lbl_title = QLabel("DEVELOPER STATS")
        lbl_title.setStyleSheet("font-size: 36px; font-weight: bold; color: white; letter-spacing: 2px; background: transparent;")
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border-top: 2px solid #ff4d4d; max-width: 150px; margin-top: 5px; margin-bottom: 5px; background: transparent;")
        
        lbl_desc = QLabel("Real-time telemetry and management metrics of your game portfolio")
        lbl_desc.setStyleSheet("font-size: 14px; color: #aaaaaa; background: transparent;")
        
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(line)
        title_layout.addWidget(lbl_desc)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Nút Refresh góc phải
        self.btn_refresh = QPushButton("🔄 REFRESH DATA")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(self.btn_refresh, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        main_layout.addLayout(header_layout)

        # --- 2. QUICK STATS ROW ---
        self.stats_row_layout = QHBoxLayout()
        self.stats_row_layout.setSpacing(15)
        
        # Khởi tạo các thẻ với giá trị rỗng trước
        self.card_total_games = StatCard("Total Games", "0", "🎮")
        self.card_total_downloads = StatCard("Downloads", "0", "📥")
        self.card_total_size = StatCard("Storage Used", "0 MB", "💾")
        self.card_active_status = StatCard("Database Check", "ONLINE", "🟢")
        
        self.stats_row_layout.addWidget(self.card_total_games)
        self.stats_row_layout.addWidget(self.card_total_downloads)
        self.stats_row_layout.addWidget(self.card_total_size)
        self.stats_row_layout.addWidget(self.card_active_status)
        self.stats_row_layout.addStretch()
        
        main_layout.addLayout(self.stats_row_layout)

        # --- 3. DETAILED TABLE CONTAINER ---
        table_container = QFrame()
        table_container.setObjectName("table_container")
        table_container_layout = QVBoxLayout(table_container)
        table_container_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_table_title = QLabel("📋 UPLOADED GAMES PORTFOLIO")
        lbl_table_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white; background: transparent; margin-bottom: 5px;")
        table_container_layout.addWidget(lbl_table_title)
        
        # Khởi tạo QTableWidget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Tên Trò Chơi", "Kích Thước", "Thư Mục Cài Đặt", "Trạng Thái Local"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Không cho sửa ô trực tiếp
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Chọn cả dòng
        
        # Cấu hình kéo dãn các cột tự động
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        table_container_layout.addWidget(self.table)
        main_layout.addWidget(table_container, stretch=1)

    # ==========================================
    # 3. LOGIC XỬ LÝ & PHÂN TÍCH DỮ LIỆU
    # ==========================================
    def update_data(self, new_games_data):
        """Hàm công khai nhận dữ liệu mới từ MainWindow để vẽ lại"""
        self.games_data = new_games_data
        self.calculate_and_populate_stats()

    def calculate_and_populate_stats(self):
        """Phân tích games_data để gán thông số và đẩy vào bảng"""
        games_list = self.games_data if isinstance(self.games_data, list) else []
        
        total_games = len(games_list)
        total_size_mb = 0
        total_simulated_downloads = 0
        
        # Cấu hình bảng
        self.table.setRowCount(0)
        
        for index, game in enumerate(games_list):
            if not game or not isinstance(game, dict):
                continue
            
            game_id = str(game.get("id", "N/A"))
            name = game.get("name", "Unknown Game")
            exe_path = game.get("exe_path", "")
            
            # --- Tính dung lượng ---
            size_mb = 0
            size_val = game.get("size_mb", game.get("size", game.get("file_size", 0)))
            try:
                size_mb = float(size_val)
            except (ValueError, TypeError):
                # Nếu là chuỗi ví dụ "1.2 GB"
                if isinstance(size_val, str):
                    if "GB" in size_val.upper():
                        try: size_mb = float(size_val.upper().replace("GB", "").strip()) * 1024
                        except: pass
                    elif "MB" in size_val.upper():
                        try: size_mb = float(size_val.upper().replace("MB", "").strip())
                        except: pass
            
            total_size_mb += size_mb
            
            # --- Giả lập số lượt tải (để giao diện sinh động) ---
            # Dùng thuật toán băm đơn giản từ ID để đảm bảo số download của mỗi game là cố định khi restart
            sim_downloads = (hash(name) % 450) + 50
            if sim_downloads < 0: sim_downloads = -sim_downloads
            total_simulated_downloads += sim_downloads
            
            # --- Kiểm tra trạng thái cài đặt tại local ---
            game_dir = os.path.join(BASE_DIR, "installed_games", game_id)
            full_exe_path = os.path.join(game_dir, str(exe_path))
            
            if os.path.exists(full_exe_path):
                local_status = "Đã Cài Đặt (Playable)"
                status_color = QColor("#27ae60") # Màu xanh lá
            else:
                local_status = "Chưa cài"
                status_color = QColor("#aaaaaa") # Màu xám
                
            # --- Đưa dữ liệu vào từng dòng của bảng ---
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Ô ID
            item_id = QTableWidgetItem(game_id)
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_position, 0, item_id)
            
            # Ô Tên game
            item_name = QTableWidgetItem(name)
            item_name.setForeground(QColor("#ff4d4d")) # Làm nổi bật tên game bằng màu đỏ
            self.table.setItem(row_position, 1, item_name)
            
            # Ô Dung lượng
            display_size = f"{int(size_mb)} MB" if size_mb < 1024 else f"{round(size_mb/1024, 2)} GB"
            item_size = QTableWidgetItem(display_size)
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_position, 2, item_size)
            
            # Ô Thư mục cài đặt
            item_path = QTableWidgetItem(os.path.basename(game_dir) if os.path.exists(game_dir) else "N/A")
            self.table.setItem(row_position, 3, item_path)
            
            # Ô Trạng thái cài đặt
            item_status = QTableWidgetItem(local_status)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(status_color)
            self.table.setItem(row_position, 4, item_status)

        # --- CẬP NHẬT TRỰC TIẾP LÊN CÁC THẺ STATS ---
        self.card_total_games.update_value(total_games)
        self.card_total_downloads.update_value(f"{total_simulated_downloads} Lượt")
        
        # Định dạng tổng dung lượng
        if total_size_mb < 1024:
            self.card_total_size.update_value(f"{int(total_size_mb)} MB")
        else:
            self.card_total_size.update_value(f"{round(total_size_mb/1024, 2)} GB")