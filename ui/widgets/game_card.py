import os
import subprocess
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QDialog, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QCursor, QDesktopServices

# Import bộ tải game từ thư mục core
from core.downloader import GameDownloader

# Xác định đường dẫn gốc của project (lùi 3 cấp: widgets -> ui -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==========================================
# 1. HỘP THOẠI DONATE & THÔNG TIN (MỚI)
# ==========================================
class DonateDialog(QDialog):
    def __init__(self, game_data, cover_path, parent=None):
        super().__init__(parent)
        self.game_data = game_data
        self.cover_path = cover_path
        
        self.setWindowTitle("Support Developer")
        self.setFixedSize(550, 320)
        self.setModal(True)
        
        self.setup_ui()
        self.apply_stylesheet()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # CỘT TRÁI: Ảnh bìa game
        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(160, 220)
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        
        if self.cover_path and os.path.exists(self.cover_path):
            pixmap = QPixmap(self.cover_path)
            self.lbl_cover.setPixmap(
                pixmap.scaled(160, 220, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.lbl_cover.setText("NO IMAGE")
            
        main_layout.addWidget(self.lbl_cover)

        # CỘT PHẢI: Thông tin và Nút bấm
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        game_name = self.game_data.get("name", "Unknown Game")
        lbl_title = QLabel(f"Trò chơi: {game_name}")
        lbl_title.setObjectName("dialog_title")
        lbl_title.setWordWrap(True)
        right_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Trò chơi này hoàn toàn miễn phí!\nTuy nhiên, nếu bạn yêu thích nó, hãy cân nhắc ủng hộ (Donate) để tiếp thêm động lực cho Nhà phát triển nhé.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #cccccc; font-size: 13px; line-height: 1.5;")
        right_layout.addWidget(lbl_desc)

        # Spacer để đẩy các nút xuống dưới
        right_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Khung chứa các nút Donate và MXH
        donate_url = self.game_data.get("donate_url", "").strip()
        socials = self.game_data.get("socials", {})
        
        # NÚT DONATE
        if donate_url:
            btn_donate = QPushButton("💖 Ủng hộ Nhà phát triển")
            btn_donate.setObjectName("btn_donate")
            btn_donate.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(donate_url)))
            right_layout.addWidget(btn_donate)

        # NÚT MẠNG XÃ HỘI (Chỉ hiện nếu có)
        socials_layout = QHBoxLayout()
        for platform, url in socials.items():
            if url.strip():
                btn_social = QPushButton(platform.capitalize())
                btn_social.setObjectName("btn_social")
                btn_social.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_social.clicked.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
                socials_layout.addWidget(btn_social)
        
        if socials_layout.count() > 0:
            right_layout.addLayout(socials_layout)

        # NÚT NO THANKS (Bỏ qua và Tải xuống)
        btn_no_thanks = QPushButton("No thanks, just take me to the downloads")
        btn_no_thanks.setObjectName("btn_no_thanks")
        btn_no_thanks.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_no_thanks.clicked.connect(self.accept) # Gọi accept() để Dialog trả về trạng thái Đồng ý tải
        right_layout.addWidget(btn_no_thanks)

        main_layout.addLayout(right_layout)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#dialog_title {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton#btn_donate {
                background-color: #e53935;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton#btn_donate:hover {
                background-color: #ff5252;
            }
            QPushButton#btn_social {
                background-color: #3b5998; /* Màu cơ bản, có thể chỉnh sau */
                color: white;
                padding: 6px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
            }
            QPushButton#btn_social:hover {
                background-color: #4c70ba;
            }
            QPushButton#btn_no_thanks {
                background-color: transparent;
                color: #aaaaaa;
                font-size: 12px;
                text-decoration: underline;
                border: none;
                padding: 5px;
                margin-top: 5px;
            }
            QPushButton#btn_no_thanks:hover {
                color: #ffffff;
            }
        """)


# ==========================================
# 2. THẺ GAME CHÍNH (ĐÃ CẬP NHẬT LUỒNG)
# ==========================================
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
        
        # Lấy đường dẫn ảnh bìa để dùng chung cho Thumbnail và Dialog
        cover_url = self.game_data.get("cover", "")
        self.cover_filename = cover_url.split("/")[-1] if cover_url else ""
        self.thumb_path = os.path.join(BASE_DIR, "assets", "covers", self.cover_filename)
        
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
        
        if self.cover_filename and os.path.exists(self.thumb_path) and os.path.isfile(self.thumb_path):
            pixmap = QPixmap(self.thumb_path)
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
        
        # 3. KÍCH THƯỚC FILE
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
                pass 

        size_val = self.game_data.get("size_mb", self.game_data.get("size", self.game_data.get("file_size", 0)))
        try:
            val_float = float(size_val)
            if val_float > 0:
                return f"{int(val_float)} MB" if val_float < 1024 else f"{round(val_float / 1024, 2)} GB"
        except (ValueError, TypeError):
            if isinstance(size_val, str) and len(size_val.strip()) > 0:
                return size_val if ("MB" in size_val.upper() or "GB" in size_val.upper()) else f"{size_val} MB"
                
        return "N/A"

    def check_game_status(self):
        """Quét ổ đĩa để cập nhật giao diện nút bấm phù hợp"""
        if os.path.exists(self.full_exe_path):
            self.status = "Play"
            self.btn_action.setText("CHƠI NGAY")
            self.btn_action.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px;")
            self.btn_action.setEnabled(True)
            self.lbl_size.setText(self.get_display_size())
        else:
            self.status = "Install"
            self.btn_action.setText("Install")
            self.btn_action.setStyleSheet("background-color: #555555; color: white; font-weight: bold; border-radius: 4px;")
            self.btn_action.setEnabled(True)

    def handle_action(self):
        """Xử lý sự kiện khi click trực tiếp vào nút chức năng"""
        if self.status == "Play":
            try:
                subprocess.Popen(self.full_exe_path, cwd=self.game_dir, shell=True)
            except Exception as e:
                print(f"Không thể khởi chạy game: {e}")
        elif self.status == "Install":
            # [ĐIỂM NÂNG CẤP]: Mở hộp thoại thông tin/Donate trước khi tải
            dialog = DonateDialog(self.game_data, self.thumb_path, self)
            
            # Nếu người dùng chọn "No thanks..." (hàm accept được gọi)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.start_download()

    def start_download(self):
        """Khởi tạo luồng tải game và kết nối tín hiệu UI"""
        download_url = self.game_data.get("download_url")
        if not download_url:
            self.btn_action.setText("LỖI LINK TẢI")
            return

        self.btn_action.setEnabled(False)
        self.btn_action.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; border-radius: 4px;")
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
            self.check_game_status() 
        else:
            print(f"Lỗi tải game {self.game_id}: {message}")
            self.check_game_status()

    def mousePressEvent(self, event):
        """Bắt sự kiện click chuột vào vùng Thẻ game để mở trang chi tiết"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.game_data)
        super().mousePressEvent(event)