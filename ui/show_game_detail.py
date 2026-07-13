import os
import urllib.request
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, QThread
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# ==========================================
# LUỒNG TẢI ẢNH NGẦM (KHẮC PHỤC TRIỆT ĐỂ LỖI SSL PYQT6)
# ==========================================
class ImageDownloader(QThread):
    data_downloaded = pyqtSignal(bytes, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            # Giả lập trình duyệt Chrome để không bị GitHub/Server từ chối
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.data_downloaded.emit(data, self.url)
        except Exception as e:
            print(f"[❌ LỖI URLLIB] URL: {self.url}")
            print(f"[❌ CHI TIẾT LỖI]: {str(e)}")
            self.data_downloaded.emit(b"", self.url)


# ==========================================
# WIDGET HIỆU ỨNG SÁNG LƯỚT QUA (SHIMMER)
# ==========================================
class ShimmerLabel(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shimmer_pos = -0.5
        self.is_loading = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_shimmer)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            border-radius: 8px; 
            border: 2px solid #ff4d4d; 
            background-color: #232323;
        """)

    def start_shimmer(self):
        self.is_loading = True
        self.clear()
        self.timer.start(30)

    def stop_shimmer(self):
        self.is_loading = False
        self.timer.stop()
        self.update()

    def update_shimmer(self):
        self._shimmer_pos += 0.04
        if self._shimmer_pos > 1.5:
            self._shimmer_pos = -0.5
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_loading:
            box_painter = QPainter(self)
            box_painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            rect = self.rect()
            box_painter.fillRect(rect, QColor("#333333"))

            w = self.width()
            x = int(self._shimmer_pos * w)

            grad = QLinearGradient(x - w * 0.3, 0, x + w * 0.3, 0)
            grad.setColorAt(0.0, QColor("#333333"))
            grad.setColorAt(0.5, QColor("#5c5c5c"))
            grad.setColorAt(1.0, QColor("#333333"))

            box_painter.fillRect(rect, grad)


# ==========================================
# GIAO DIỆN CHI TIẾT GAME
# ==========================================
class GameDetailPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, base_dir, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir

        self.media_list = []
        self.current_media_index = 0
        self.current_media_url = ""
        
        # Biến lưu trữ luồng tải ảnh hiện tại
        self.downloader = None

        # --- BẮT BUỘC ĐỂ QWIDGET NHẬN MÀU NỀN GRADIENT TỪ STYLESHEET ---
        self.setObjectName("GameDetailPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # --------------------------------------------------------------

        self.setup_ui()

    def setup_ui(self):
        # Thiết lập font chung và nền Gradient dọc (Đen - Xám - Đen) cho toàn bộ trang Chi Tiết Game
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Montenegrin Gothic One', 'Orbitron', sans-serif; 
            }
            
            /* --- NỀN GRADIENT ĐEN - XÁM - ĐEN DỌC --- */
            QWidget#GameDetailPage {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0.0 #111111,
                    stop: 0.5 #2d2d2d,
                    stop: 1.0 #111111
                );
            }
            
            /* Đảm bảo tất cả các nhãn văn bản có nền trong suốt để lộ lớp gradient bên dưới */
            QLabel {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)

        # --- NÚT QUAY LẠI (Đã mở rộng lên 220px để không bị cắt chữ) ---
        self.btn_back = QPushButton("⬅ QUAY LẠI CỬA HÀNG")
        self.btn_back.setStyleSheet("""
            QPushButton {
                color: #ff4d4d; font-size: 14px; font-weight: bold; 
                text-align: left; padding: 0px; background: transparent; border: none;
            }
            QPushButton:hover { color: #ff6666; text-decoration: underline; }
        """)
        self.btn_back.setFixedWidth(220)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(self.btn_back)

        # ================= KHU VỰC THÔNG TIN CHÍNH (HEADER) =================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(30)

        media_container = QVBoxLayout()
        media_container.setSpacing(8)

        # 1. PHÓNG TO ẢNH GAME LÊN 480x270 (CHẨN 16:9)
        self.media_stack = QStackedWidget()
        self.media_stack.setFixedSize(480, 270)

        self.lbl_thumbnail = ShimmerLabel()
        self.media_stack.addWidget(self.lbl_thumbnail)

        self.video_preview_widget = QFrame()
        self.video_preview_widget.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a; 
                border-radius: 8px; 
                border: 2px solid #ff4d4d;
            }
        """)
        video_layout = QVBoxLayout(self.video_preview_widget)
        video_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_layout.setSpacing(15)

        lbl_video_icon = QLabel("🎬 VIDEO TRAILER / TEASER")
        lbl_video_icon.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: bold; border: none; background: transparent;"
        )
        lbl_video_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_play_video = QPushButton("▶ Xem Trên Trình Duyệt")
        self.btn_play_video.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_video.setStyleSheet("""
            QPushButton {
                background-color: #ff4d4d; color: white; 
                font-weight: bold; font-size: 14px;
                padding: 10px 20px; border-radius: 5px; border: none;
            }
            QPushButton:hover { background-color: #ff6666; }
        """)
        self.btn_play_video.clicked.connect(self.open_video_url)

        video_layout.addWidget(lbl_video_icon)
        video_layout.addWidget(self.btn_play_video)

        self.media_stack.addWidget(self.video_preview_widget)

        nav_layout = QHBoxLayout()
        self.btn_prev_media = QPushButton("◀")
        self.btn_next_media = QPushButton("▶")
        self.lbl_media_indicator = QLabel("0/0")
        self.lbl_media_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_media_indicator.setStyleSheet(
            "color: #aaa; font-size: 13px; font-weight: bold; background: transparent;"
        )

        for btn in (self.btn_prev_media, self.btn_next_media):
            btn.setFixedSize(35, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { background-color: #333333; color: white; border: 1px solid #555555; border-radius: 4px; font-weight: bold;}
                QPushButton:hover { background-color: #ff4d4d; border-color: #ff4d4d; }
            """)

        self.btn_prev_media.clicked.connect(self.prev_media)
        self.btn_next_media.clicked.connect(self.next_media)

        nav_layout.addWidget(self.btn_prev_media)
        nav_layout.addWidget(self.lbl_media_indicator, stretch=1)
        nav_layout.addWidget(self.btn_next_media)

        media_container.addWidget(self.media_stack)
        media_container.addLayout(nav_layout)
        header_layout.addLayout(media_container)

        # --- CỘT BÊN PHẢI (TÊN GAME -> LINE ĐỎ -> NÚT INSTALL) ---
        info_layout = QVBoxLayout()
        info_layout.setSpacing(12)

        self.detail_title = QLabel("Game Title")
        self.detail_title.setStyleSheet(
            "font-size: 38px; font-weight: 800; color: white; margin-bottom: 0px;"
        )
        self.detail_title.setWordWrap(True)
        info_layout.addWidget(self.detail_title)

        # 2. ĐƯỜNG LINE ĐỎ MẢNH NGĂN CÁCH TÊN GAME VÀ NÚT INSTALL
        self.red_separator = QFrame()
        self.red_separator.setFixedHeight(2)
        self.red_separator.setStyleSheet("background-color: #ff4d4d; border: none;")
        info_layout.addWidget(self.red_separator)

        info_layout.addStretch()

        self.detail_btn_action = QPushButton("Install")
        self.detail_btn_action.setFixedSize(200, 50) # Làm nút to ra xíu cho cân với ảnh lớn
        self.detail_btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        info_layout.addWidget(self.detail_btn_action)

        header_layout.addLayout(info_layout, stretch=1)
        layout.addLayout(header_layout)

        # ================= KHU VỰC MÔ TẢ (ĐƯỢC GOM VÀO KHUNG BOX) =================
        # 3. TAO KHUNG MÔ TẢ RIÊNG BIỆT (BOX FRAME)
        self.desc_frame = QFrame()
        self.desc_frame.setStyleSheet("""
            QFrame#DescBox {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        self.desc_frame.setObjectName("DescBox")
        
        desc_layout = QVBoxLayout(self.desc_frame)
        desc_layout.setContentsMargins(20, 20, 20, 20)
        desc_layout.setSpacing(12)

        lbl_about = QLabel("■ VỀ TRÒ CHƠI NÀY")
        lbl_about.setStyleSheet(
            "color: #ff4d4d; font-size: 14px; font-weight: bold; letter-spacing: 1px; border: none; background: transparent;"
        )
        desc_layout.addWidget(lbl_about)

        self.detail_desc = QLabel()
        self.detail_desc.setStyleSheet(
            "color: #dddddd; font-size: 15px; line-height: 1.6; border: none; background: transparent;"
        )
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        desc_layout.addWidget(self.detail_desc)

        layout.addWidget(self.desc_frame, stretch=1)

    def set_game_data(self, game_data):
        self.detail_title.setText(game_data.get("name", "Unknown Game"))

        status_text = game_data.get("status", "Install")
        self.detail_btn_action.setText(status_text)
        if status_text == "Play":
            self.detail_btn_action.setStyleSheet(
                "background-color: #27ae60; color: white; font-size: 18px; font-weight: bold; border-radius: 5px; border: none;"
            )
        elif status_text == "Update":
            self.detail_btn_action.setStyleSheet(
                "background-color: #f39c12; color: white; font-size: 18px; font-weight: bold; border-radius: 5px; border: none;"
            )
        else:
            self.detail_btn_action.setStyleSheet(
                "background-color: #ff4d4d; color: white; font-size: 18px; font-weight: bold; border-radius: 5px; border: none;"
            )

        default_desc = "Trò chơi này hiện chưa có bài viết mô tả chi tiết từ quản trị viên Vangrok.\nHãy nhấn nút bên trên để cài đặt và trải nghiệm cùng bạn bè ngay!"
        self.detail_desc.setText(game_data.get("description", default_desc))

        self.media_list.clear()
        covers = game_data.get("cover", [])
        if isinstance(covers, str) and covers.strip():
            self.media_list.append(covers)
        elif isinstance(covers, list):
            self.media_list.extend(covers)

        video_url = game_data.get("video_url", "")
        if video_url:
            self.media_list.append(video_url)

        self.current_media_index = 0
        self.update_media_viewer()

    def update_media_viewer(self):
        if not self.media_list:
            self.media_stack.setCurrentIndex(0)
            self.lbl_thumbnail.stop_shimmer()
            self.lbl_thumbnail.setText("NO MEDIA")
            self.lbl_media_indicator.setText("0/0")
            return

        self.lbl_media_indicator.setText(
            f"{self.current_media_index + 1}/{len(self.media_list)}"
        )
        self.current_media_url = self.media_list[self.current_media_index]

        is_video = (
            self.current_media_url.endswith((".mp4", ".webm", ".avi", ".mkv"))
            or "youtube.com" in self.current_media_url
            or "youtu.be" in self.current_media_url
        )

        if is_video:
            self.media_stack.setCurrentIndex(1)
        else:
            self.media_stack.setCurrentIndex(0)
            self.load_image_async(self.current_media_url)

    # --- HÀM TẢI ẢNH ĐÃ ĐƯỢC THAY THẾ BẰNG QTHREAD ---
    def load_image_async(self, url):
        self.lbl_thumbnail.start_shimmer()

        # Nếu là đường dẫn tệp cục bộ (Local file)
        if not url.startswith("http"):
            full_path = os.path.join(self.base_dir, url)
            if os.path.exists(full_path):
                self.lbl_thumbnail.stop_shimmer()
                self._set_pixmap_scaled(QPixmap(full_path))
            else:
                self.lbl_thumbnail.stop_shimmer()
                self.lbl_thumbnail.setText("LỖI ĐƯỜNG DẪN ẢNH")
            return

        # Khởi tạo luồng tải ảnh ngầm bằng urllib
        self.downloader = ImageDownloader(url, self)
        self.downloader.data_downloaded.connect(self.on_image_downloaded)
        self.downloader.start()

    # --- NHẬN DỮ LIỆU TỪ LUỒNG TẢI ẢNH ---
    def on_image_downloaded(self, data, url):
        # Kiểm tra: Nếu người dùng bấm lướt nhanh sang ảnh khác, bỏ qua kết quả của ảnh cũ
        if url != self.current_media_url:
            return

        self.lbl_thumbnail.stop_shimmer()

        if not data:
            self.lbl_thumbnail.setText("LỖI MẠNG")
            return

        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if pixmap.isNull():
            self.lbl_thumbnail.setText("ẢNH BỊ LỖI")
            print(f"[❌ LỖI DỮ LIỆU] File tải về không phải ảnh hợp lệ: {url}")
        else:
            self._set_pixmap_scaled(pixmap)

    def _set_pixmap_scaled(self, pixmap):
        if not pixmap.isNull():
            self.lbl_thumbnail.setPixmap(
                pixmap.scaled(
                    self.lbl_thumbnail.width(),
                    self.lbl_thumbnail.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def open_video_url(self):
        if self.current_media_url:
            QDesktopServices.openUrl(QUrl(self.current_media_url))

    def prev_media(self):
        if self.media_list:
            self.current_media_index = (self.current_media_index - 1) % len(
                self.media_list
            )
            self.update_media_viewer()

    def next_media(self):
        if self.media_list:
            self.current_media_index = (self.current_media_index + 1) % len(
                self.media_list
            )
            self.update_media_viewer()