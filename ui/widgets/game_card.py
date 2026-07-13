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
        self.game_dir = os.path.join(BASE_DIR, "installed_games", str(self.game_id))
        self.full_exe_path = os.path.join(self.game_dir, str(self.exe_path))
        
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
        
        # 1. KHU VỰC THUMBNAIL
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedHeight(130)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; border-radius: 5px;")
        
        cover_url = self.game_data.get("cover", "")
        cover_filename = cover_url.split("/")[-1] if cover_url else ""
        thumb_path = os.path.join(BASE_DIR, "assets", "covers", cover_filename)
        
        if cover_filename and os.path.exists(thumb_path) and os.path.isfile(thumb_path):
            pixmap = QPixmap(thumb_path)
            self.lbl_thumb.setPixmap(
                pixmap.scaled(160, 130, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.lbl_thumb.setText("NO IMAGE")
            self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; color: #666666; font-weight: bold; border-radius: 5px;")
            
        layout.addWidget(self.lbl_thumb)
        
        # 2. TIÊU ĐỀ GAME
        lbl_title = QLabel(self.game_data.get("name", "Unknown Game"))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        lbl_title.setWordWrap(True)
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignTop)
        
        layout.addStretch()
        
        # 3. KÍCH THƯỚC FILE (Đã fix để tự tính dung lượng ổ đĩa thực hoặc quét chuẩn key)
        size_str = self.get_display_size()
        self.lbl_size = QLabel(size_str)
        self.lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_size.setStyleSheet("font-size: 11px; color: #aaaaaa; font-weight: bold;")
        layout.addWidget(self.lbl_size)
        
        # 4. NÚT ACTION (Play / Install)
        self.btn_action = QPushButton("Kiểm tra...")
        self.btn_action.setObjectName("btn_action")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setFixedHeight(30)
        self.btn_action.clicked.connect(self.handle_action)
        
        layout.addWidget(self.btn_action)

    def get_display_size(self):
        """Hàm thông minh tự tính dung lượng thực trên máy hoặc đọc từ data JSON"""
        # Ưu tiên 1: Nếu game đã cài đặt, quét luôn thư mục thực tế trên ổ cứng (ra đúng số như 771 MB)
        if os.path.exists(self.game_dir):
            total_size = 0
            try:
                for dirpath, _, filenames in os.walk(self.game_dir):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            total_size += os.path.getsize(fp)
                size_in_mb = round(total_size / (1024 * 1024))
                if size_in_mb > 0:
                    return f"{size_in_mb} MB" if size_in_mb < 1024 else f"{round(size_in_mb / 1024, 2)} GB"
            except Exception:
                pass # Nếu lỗi quyền đọc file thì bỏ qua chạy xuống lấy từ JSON

        # Ưu tiên 2: Lấy từ data JSON (quét tất cả các key dễ bị đặt nhầm)
        size_val = self.game_data.get("size_mb", self.game_data.get("size", self.game_data.get("file_size", 0)))
        try:
            val_float = float(size_val)
            if val_float > 0:
                return f"{int(val_float)} MB" if val_float < 1024 else f"{round(val_float / 1024, 2)} GB"
        except (ValueError, TypeError):
            # Nếu trong JSON ghi dạng chữ sẵn như "771 MB" hay "1.2 GB"
            if isinstance(size_val, str) and len(size_val.strip()) > 0:
                return size_val if ("MB" in size_val.upper() or "GB" in size_val.upper()) else f"{size_val} MB"
                
        return "N/A"

    def check_game_status(self):
        """Quét ổ đĩa để cập nhật giao diện nút bấm phù hợp"""
        if os.path.exists(self.full_exe_path):
            self.status = "Play"
            self.btn_action.setText("CHƠI NGAY")
            self.btn_action.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
            self.btn_action.setEnabled(True)
            # Khi kiểm tra thấy đã cài đặt, cập nhật lại nhãn dung lượng cho chính xác 100%
            self.lbl_size.setText(self.get_display_size())
        else:
            self.status = "Install"
            self.btn_action.setText("Install")
            self.btn_action.setStyleSheet("background-color: #555555; color: white; font-weight: bold;")
            self.btn_action.setEnabled(True)

    def handle_action(self):
        """Xử lý sự kiện khi click trực tiếp vào nút chức năng"""
        if self.status == "Play":
            try:
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
            self.check_game_status() # Chuyển trạng thái sang nút "CHƠI NGAY" và update lại dung lượng thật
        else:
            print(f"Lỗi tải game {self.game_id}: {message}")
            self.check_game_status()

    def mousePressEvent(self, event):
        """Bắt sự kiện click chuột vào vùng Thẻ game để mở trang chi tiết"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.game_data)
        super().mousePressEvent(event)