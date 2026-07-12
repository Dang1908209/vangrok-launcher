import os
import subprocess
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QCursor
# Import bộ tải game từ thư mục core
from core.downloader import GameDownloader

# Xác định đường dẫn gốc của project (lùi 3 cấp: widgets -> ui -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class GameCard(QFrame):
    # Tạo signal gửi toàn bộ dữ liệu của game (dict) lên MainWindow khi nhấp chuột
    card_clicked = pyqtSignal(dict)

    def __init__(self, game_data):
        super().__init__()
        self.game_data = game_data
        self.game_id = self.game_data.get("id")
        self.exe_path = self.game_data.get("exe_path")
        
        # Đường dẫn thư mục cài đặt và file thực thi của game này
        self.game_dir = os.path.join(BASE_DIR, "installed_games", self.game_id)
        self.full_exe_path = os.path.join(self.game_dir, self.exe_path)
        
        self.setFixedSize(180, 260) # Tăng kích thước thẻ để chứa đẹp ảnh thumbnail
        self.setObjectName("game_card")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)) # Con trỏ biến thành bàn tay
        
        self.downloader = None
        self.status = "Install" # Trạng thái mặc định
        
        self.setup_ui()
        self.check_game_status() # Kiểm tra xem game đã được cài trước đó chưa
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 1. KHU VỰC THUMBNAIL (Sửa đổi từ "thumbnail" -> "cover")
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedHeight(130)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; border-radius: 5px;")
        
        # Lấy tên file ảnh từ link URL raw
        cover_url = self.game_data.get("cover", "")
        cover_filename = cover_url.split("/")[-1] if cover_url else ""
        thumb_path = os.path.join(BASE_DIR, "assets", "covers", cover_filename)
        
        if cover_filename and os.path.exists(thumb_path) and os.path.isfile(thumb_path):
            pixmap = QPixmap(thumb_path)
            self.lbl_thumb.setPixmap(
                pixmap.scaled(160, 130, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            # Fallback nếu không có ảnh cục bộ
            self.lbl_thumb.setText("NO IMAGE")
            self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; color: #666666; font-weight: bold; border-radius: 5px;")
            
        layout.addWidget(self.lbl_thumb)
        
        # 2. TIÊU ĐỀ GAME (Sửa đổi từ "title" -> "name")
        lbl_title = QLabel(self.game_data.get("name", "Unknown Game"))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignTop)
        
        layout.addStretch()
        
        # 3. KÍCH THƯỚC FILE (Sửa đổi từ "size" -> "size_mb")
        size_mb = self.game_data.get("size_mb", 0)
        lbl_size = QLabel(f"{size_mb} MB")
        lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_size.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(lbl_size)
        
        # 4. NÚT ACTION (Play / Install)
        self.btn_action = QPushButton("Kiểm tra...")
        self.btn_action.setObjectName("btn_action")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setFixedHeight(30)
        self.btn_action.clicked.connect(self.handle_action) # Kết nối hành động click nút
        
        layout.addWidget(self.btn_action)

    def check_game_status(self):
        """Quét ổ đĩa để cập nhật giao diện nút bấm phù hợp"""
        if os.path.exists(self.full_exe_path):
            self.status = "Play"
            self.btn_action.setText("CHƠI NGAY")
            self.btn_action.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
            self.btn_action.setEnabled(True)
        else:
            self.status = "Install"
            self.btn_action.setText("CÀI ĐẶT")
            self.btn_action.setStyleSheet("background-color: #555555; color: white; font-weight: bold;")
            self.btn_action.setEnabled(True)

    def handle_action(self):
        """Xử lý sự kiện khi click trực tiếp vào nút chức năng"""
        if self.status == "Play":
            try:
                # Chạy file game (.exe) ngầm và đặt thư mục làm việc (cwd) tại folder game đó
                subprocess.Popen(self.full_exe_path, cwd=self.game_dir, shell=True)
            except Exception as e:
                print(f"Không thể khởi chạy game: {e}")
        elif self.status == "Install":
            self.start_download()

    def start_download(self):
        """Khởi tạo luồng tải game và kết nối tín hiệu UI"""
        download_url = self.game_data.get("download_url")
        if not download_url:
            self.btn_action.setText("LỖI LINK TẢI")
            return

        self.btn_action.setEnabled(False)
        self.btn_action.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        self.btn_action.setText("0%")

        # Khởi tạo Thread chuyên tải dữ liệu
        self.downloader = GameDownloader(download_url, self.game_id, BASE_DIR)
        self.downloader.progress_signal.connect(self.update_download_progress)
        self.downloader.finished_signal.connect(self.download_finished)
        self.downloader.start()

    def update_download_progress(self, percent):
        """Cập nhật phần trăm trực tiếp lên nút bấm"""
        self.btn_action.setText(f"TẢI: {percent}%")

    def download_finished(self, success, message):
        """Báo cáo kết quả sau khi tải hoàn tất"""
        if success:
            self.check_game_status() # Chuyển trạng thái sang nút "CHƠI NGAY"
        else:
            print(f"Lỗi tải game {self.game_id}: {message}")
            self.check_game_status() # Reset giao diện về trạng thái ban đầu

    def mousePressEvent(self, event):
        """Bắt sự kiện click chuột vào vùng Thẻ game để mở trang chi tiết"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.game_data)
        super().mousePressEvent(event)