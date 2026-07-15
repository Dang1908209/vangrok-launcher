import os
import re
import urllib.request
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QLinearGradient,
    QPainter,
    QPixmap,
    QCursor
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QSizePolicy
)


# ==========================================
# CÁC HÀM HỖ TRỢ XỬ LÝ YOUTUBE
# ==========================================
def get_youtube_id(url):
    """Trích xuất ID của video từ link YouTube"""
    regex = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    return match.group(1) if match else None

def get_media_thumbnail_url(url):
    """Tự động lấy ảnh đại diện: Nếu là YouTube thì lấy ảnh của YouTube, nếu là ảnh thì giữ nguyên"""
    yt_id = get_youtube_id(url)
    if yt_id:
        return f"https://img.youtube.com/vi/{yt_id}/mqdefault.jpg"
    return url


# ==========================================
# LUỒNG TẢI ẢNH NGẦM
# ==========================================
class ImageDownloader(QThread):
    data_downloaded = pyqtSignal(bytes, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        " AppleWebKit/537.36 (KHTML, like Gecko)"
                        " Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.data_downloaded.emit(data, self.url)
        except Exception as e:
            print(f"[❌ LỖI URLLIB] URL: {self.url} | Lỗi: {str(e)}")
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
            border: 2px solid #333333; 
            background-color: #1a1a1a; color: #888; font-weight: bold;
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
            box_painter.fillRect(rect, QColor("#1a1a1a"))

            w = self.width()
            x = int(self._shimmer_pos * w)
            grad = QLinearGradient(x - w * 0.3, 0, x + w * 0.3, 0)
            grad.setColorAt(0.0, QColor("#1a1a1a"))
            grad.setColorAt(0.5, QColor("#3a3a3a"))
            grad.setColorAt(1.0, QColor("#1a1a1a"))
            box_painter.fillRect(rect, grad)


# ==========================================
# GIAO DIỆN CHI TIẾT GAME (ĐÃ NÂNG CẤP ĐẦY ĐỦ TÍNH NĂNG)
# ==========================================
class GameDetailPage(QWidget):
    back_requested = pyqtSignal()
    # Tín hiệu phát ra khi nhấn nút CHƠI NGAY hoặc CÀI ĐẶT (gửi kèm dữ liệu game và trạng thái)
    action_requested = pyqtSignal(dict, str)

    def __init__(self, base_dir, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.current_game_data = {}
        self.current_status = "Install"

        self.media_list = []
        self.thumbnail_widgets = []
        self.current_media_index = 0
        self.current_media_url = ""

        # [MỚI] Biến lưu trữ link Donate & Mạng xã hội của game hiện tại
        self.current_donate_url = ""
        self.current_fb_url = ""
        self.current_discord_url = ""
        self.current_web_url = ""

        # Biến lưu trữ luồng tải ảnh hiện tại
        self.downloader = None

        self.setObjectName("GameDetailPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setup_ui()

    def setup_ui(self):
        # Thiết lập font chung và nền Gradient dọc (Đen - Xám - Đen)
        self.setStyleSheet("""
            QWidget { 
                font-family: 'Montenegrin Gothic One', 'Orbitron', 'Segoe UI', sans-serif; 
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
            
            /* Đảm bảo tất cả các nhãn văn bản có nền trong suốt */
            QLabel {
                background: transparent;
            }
            QLabel { background: transparent; }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #1a1a1a; width: 8px; }
            QScrollBar::handle:vertical { background: #444; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #ff4d4d; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # --- NÚT QUAY LẠI ---
        self.btn_back = QPushButton("⬅ QUAY LẠI CỬA HÀNG")
        self.btn_back.setStyleSheet("""
            QPushButton { color: #ff4d4d; font-size: 14px; font-weight: bold; text-align: left; padding: 0px; background: transparent; border: none; }
            QPushButton:hover { color: #ff6666; text-decoration: underline; }
        """)
        self.btn_back.setFixedWidth(220)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.on_back_clicked)
        layout.addWidget(self.btn_back)

        # ================= KHU VỰC THÔNG TIN CHÍNH (HEADER) =================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(25)

        # --- CỘT TRÁI: MEDIA GALLERY (MÀN HÌNH CHÍNH + DANH SÁCH BÊN PHẢI) ---
        media_gallery_layout = QHBoxLayout()
        media_gallery_layout.setSpacing(10)

        # 1. PHÓNG TO ẢNH GAME LÊN 480x270 (CHUẨN 16:9)
        self.media_stack = QStackedWidget()
        self.media_stack.setFixedSize(600, 338)
        self.media_stack.setStyleSheet("background-color: #111; border-radius: 8px; border: 2px solid #333;")

        self.lbl_main_image = ShimmerLabel()
        self.lbl_main_image.setStyleSheet("border-radius: 8px; border: none;")
        self.media_stack.addWidget(self.lbl_main_image) # Index 0: Hiển thị ảnh

        # Index 1: Trình phát Video (QWebEngineView)
        if WEB_ENGINE_AVAILABLE:
            self.video_player = QWebEngineView()
            self.video_player.setStyleSheet("background-color: #000; border-radius: 8px;")
            self.media_stack.addWidget(self.video_player)
        else:
            # Fallback nếu chưa cài PyQt6-WebEngine
            self.fallback_video_frame = QFrame()
            fb_layout = QVBoxLayout(self.fallback_video_frame)
            fb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_err = QLabel("⚠️ Cần cài đặt 'PyQt6-WebEngine' để xem Video trực tiếp")
            lbl_err.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
            btn_open_ext = QPushButton("🎬 Mở Trình Duyệt Để Xem")
            btn_open_ext.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open_ext.setStyleSheet("background-color: #ff4d4d; color: white; padding: 10px 20px; font-weight: bold; border-radius: 5px;")
            btn_open_ext.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.media_list[self.current_media_index])))
            fb_layout.addWidget(lbl_err)
            fb_layout.addWidget(btn_open_ext)
            self.media_stack.addWidget(self.fallback_video_frame)

        media_gallery_layout.addWidget(self.media_stack)

        self.btn_play_video = QPushButton("▶ Xem Trailer (MP4 / YouTube)")
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

        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QVBoxLayout(self.thumbnails_container)
        self.thumbnails_layout.setContentsMargins(0, 0, 5, 0)
        self.thumbnails_layout.setSpacing(8)
        self.thumbnails_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.thumbnails_container)
        media_gallery_layout.addWidget(self.scroll_area)

        header_layout.addLayout(media_gallery_layout)

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

        # --- CỘT BÊN PHẢI (TÊN GAME -> LINE ĐỎ -> NÚT ACTION -> DONATE & SOCIALS) ---
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        # Tên Game
        self.detail_title = QLabel("Game Title")
        self.detail_title.setStyleSheet("font-size: 34px; font-weight: 800; color: white; margin-bottom: 0px;")
        self.detail_title.setWordWrap(True)
        info_layout.addWidget(self.detail_title)

        # 2. ĐƯỜNG LINE ĐỎ MẢNH NGĂN CÁCH TÊN GAME
        self.red_separator = QFrame()
        self.red_separator.setFixedHeight(2)
        self.red_separator.setStyleSheet("background-color: #ff4d4d; border: none;")
        info_layout.addWidget(self.red_separator)

        info_layout.addStretch()

        # NÚT ACTION (CÀI ĐẶT / CHƠI NGAY)
        self.detail_btn_action = QPushButton("Install")
        self.detail_btn_action.setFixedHeight(50)
        self.detail_btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.detail_btn_action.clicked.connect(self.on_action_clicked)
        info_layout.addWidget(self.detail_btn_action)

        # =========================================================================
        # [MỚI] KHU VỰC NÚT DONATE VÀ MẠNG XÃ HỘI (FACEBOOK, DISCORD, WEB)
        # =========================================================================
        self.btn_donate = QPushButton("💖 ỦNG HỘ NHÀ PHÁT TRIỂN")
        self.btn_donate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_donate.setFixedHeight(40)
        self.btn_donate.setStyleSheet("""
            QPushButton {
                background-color: #e84393; color: white; font-weight: bold; 
                font-size: 14px; border-radius: 5px; border: 1px solid #fd79a8;
            }
            QPushButton:hover { background-color: #fd79a8; }
        """)
        self.btn_donate.clicked.connect(lambda: self.open_external_link(self.current_donate_url))
        info_layout.addWidget(self.btn_donate)

        # Hàng nút mạng xã hội (Nằm ngang)
        self.socials_layout = QHBoxLayout()
        self.socials_layout.setSpacing(8)

        social_style = """
            QPushButton {
                background-color: #2d3436; color: #dfe6e9; font-weight: bold; 
                font-size: 12px; padding: 8px 5px; border-radius: 4px; border: 1px solid #636e72;
            }
            QPushButton:hover { background-color: #636e72; color: white; border-color: #ff4d4d; }
        """

        self.btn_fb = QPushButton("📘 Facebook")
        self.btn_fb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fb.setStyleSheet(social_style)
        self.btn_fb.clicked.connect(lambda: self.open_external_link(self.current_fb_url))

        self.btn_discord = QPushButton("🎮 Discord")
        self.btn_discord.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discord.setStyleSheet(social_style)
        self.btn_discord.clicked.connect(lambda: self.open_external_link(self.current_discord_url))

        self.btn_web = QPushButton("🌐 Website")
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.setStyleSheet(social_style)
        self.btn_web.clicked.connect(lambda: self.open_external_link(self.current_web_url))

        self.socials_layout.addWidget(self.btn_fb)
        self.socials_layout.addWidget(self.btn_discord)
        self.socials_layout.addWidget(self.btn_web)

        info_layout.addLayout(self.socials_layout)
        # =========================================================================

        header_layout.addLayout(info_layout, stretch=1)
        layout.addLayout(header_layout)

        # ================= KHU VỰC MÔ TẢ (BOX FRAME) =================
        self.desc_frame = QFrame()
        self.desc_frame.setStyleSheet("QFrame#DescBox { background-color: #1a1a1a; border: 1px solid #333; border-radius: 8px; }")
        self.desc_frame.setObjectName("DescBox")

        desc_layout = QVBoxLayout(self.desc_frame)
        desc_layout.setContentsMargins(20, 15, 20, 15)
        desc_layout.setSpacing(8)

        lbl_about = QLabel("■ VỀ TRÒ CHƠI NÀY")
        lbl_about.setStyleSheet("color: #ff4d4d; font-size: 14px; font-weight: bold; letter-spacing: 1px;")
        desc_layout.addWidget(lbl_about)

        self.detail_desc = QLabel()
        self.detail_desc.setStyleSheet("color: #dddddd; font-size: 14px; line-height: 1.5;")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        desc_layout.addWidget(self.detail_desc)

        layout.addWidget(self.desc_frame, stretch=1)

    def set_game_data(self, game_data):
        """Hàm nhận dữ liệu game và tự động kiểm tra trạng thái cài đặt thực tế"""
        self.current_game_data = game_data
        self.detail_title.setText(game_data.get("name", "Unknown Game"))
        
        # [MỚI] Cập nhật Developer Name
        dev_name = game_data.get("developer", game_data.get("dev", "Unknown Developer"))
        self.detail_dev.setText(f"by {dev_name}")

        # =========================================================================
        # KIỂM TRA TRỰC TIẾP TRÊN Ổ CỨNG XEM GAME ĐÃ CÀI CHƯA
        # =========================================================================
        game_id = game_data.get("id")
        exe_path = game_data.get("exe_path")

        if game_id and exe_path:
            full_exe_path = os.path.join(
                self.base_dir, "installed_games", str(game_id), str(exe_path)
            )
            # Nếu file .exe thực sự tồn tại trong ổ đĩa -> Đổi trạng thái thành Play
            if os.path.exists(full_exe_path):
                self.current_status = "Play"
            else:
                self.current_status = game_data.get("status", "Install")
        else:
            self.current_status = game_data.get("status", "Install")

        # Cập nhật nút bấm Action theo đúng trạng thái vừa quét được
        self.update_action_button_ui()

        # =========================================================================
        # [MỚI] CẬP NHẬT TRẠNG THÁI ẨN/HIỆN CHO NÚT DONATE & MẠNG XÃ HỘI
        # =========================================================================
        self.current_donate_url = game_data.get("donate_url", "").strip()
        self.btn_donate.setVisible(bool(self.current_donate_url))

        socials = game_data.get("socials", {})
        if not isinstance(socials, dict):
            socials = {}

        self.current_fb_url = socials.get("facebook", "").strip()
        self.btn_fb.setVisible(bool(self.current_fb_url))

        self.current_discord_url = socials.get("discord", "").strip()
        self.btn_discord.setVisible(bool(self.current_discord_url))

        self.current_web_url = socials.get("website", "").strip()
        self.btn_web.setVisible(bool(self.current_web_url))
        # =========================================================================

        # Hiển thị mô tả
        default_desc = (
            "Trò chơi này hiện chưa có bài viết mô tả chi tiết từ quản trị"
            " viên Vangrok.\nHãy nhấn nút bên trên để cài đặt và trải"
            " nghiệm cùng bạn bè ngay!"
        )
        self.detail_desc.setText(game_data.get("description", default_desc))

        # Tải danh sách hình ảnh & video
        self.media_list.clear()
        video_url = game_data.get("video_url", "").strip()
        if video_url:
            self.media_list.append(video_url) # Ưu tiên để Video lên đầu danh sách

        covers = game_data.get("cover", [])
        if isinstance(covers, str) and covers.strip():
            if covers.strip() not in self.media_list: self.media_list.append(covers.strip())
        elif isinstance(covers, list):
            for c in covers:
                if c and str(c).strip() not in self.media_list: self.media_list.append(str(c).strip())

        self.build_thumbnails_gallery()
        self.select_media(0) # Mặc định chọn mục đầu tiên

    def build_thumbnails_gallery(self):
        """Tạo danh sách thẻ Thumbnail xếp dọc bên phải"""
        # Xóa các widget cũ trong gallery
        while self.thumbnails_layout.count():
            item = self.thumbnails_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.thumbnail_widgets.clear()

    def update_action_button_ui(self):
        """Cập nhật Giao diện (Màu sắc, chữ) của nút Action dựa theo self.current_status"""
        if self.current_status == "Play":
            self.detail_btn_action.setText("CHƠI NGAY")
            self.detail_btn_action.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60; color: white; 
                    font-size: 18px; font-weight: bold; border-radius: 5px; border: none;
                }
                QPushButton:hover { background-color: #2ecc71; }
            """)
        elif self.current_status == "Update":
            self.detail_btn_action.setText("CẬP NHẬT")
            self.detail_btn_action.setStyleSheet("""
                QPushButton {
                    background-color: #f39c12; color: white; 
                    font-size: 18px; font-weight: bold; border-radius: 5px; border: none;
                }
                QPushButton:hover { background-color: #f1c40f; }
            """)
        else:
            self.current_status = "Install"
            self.detail_btn_action.setText("CÀI ĐẶT")
            self.detail_btn_action.setStyleSheet("""
                QPushButton {
                    background-color: #ff4d4d; color: white; 
                    font-size: 18px; font-weight: bold; border-radius: 5px; border: none;
                }
                QPushButton:hover { background-color: #ff6666; }
            """)

    def on_action_clicked(self):
        """Khi bấm nút CÀI ĐẶT hoặc CHƠI NGAY trong trang chi tiết"""
        self.action_requested.emit(self.current_game_data, self.current_status)

    # [MỚI] Hàm mở link bên ngoài (Donate, FB, Discord...)
    def open_external_link(self, url):
        if url and isinstance(url, str) and url.strip():
            QDesktopServices.openUrl(QUrl(url.strip()))

    def update_media_viewer(self):
        if not self.media_list:
            self.media_stack.setCurrentIndex(0)
            self.lbl_thumbnail.stop_shimmer()
            self.lbl_thumbnail.setText("NO MEDIA")
            self.lbl_media_indicator.setText("0/0")
            return

    def select_media(self, index):
        """Khi click vào ảnh/video nào bên cột phải thì hiển thị lên màn hình chính bên trái"""
        if not self.media_list or index >= len(self.media_list): return

        # [CẬP NHẬT] Nhận diện cả file MP4 tải về từ GitHub Release lẫn YouTube
        is_video = (
            self.current_media_url.lower().endswith((".mp4", ".webm", ".avi", ".mkv"))
            or "youtube.com" in self.current_media_url.lower()
            or "youtu.be" in self.current_media_url.lower()
        )

        self.current_media_index = index
        url = self.media_list[index]

        yt_id = get_youtube_id(url)
        is_mp4 = url.lower().endswith(('.mp4', '.webm'))

        # Nếu là Video (YouTube hoặc MP4) -> Bật Trình phát Video
        if yt_id or is_mp4:
            self.media_stack.setCurrentIndex(1)
            if WEB_ENGINE_AVAILABLE:
                if yt_id:
                    # Nhúng YouTube Player với chế độ tự động phát (autoplay=1)
                    embed_html = f"""
                    <body style="margin:0; background-color:black;">
                        <iframe width="100%" height="100%" src="https://www.youtube.com/embed/{yt_id}?autoplay=1&rel=0" 
                        frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
                    </body>
                    """
                    self.video_player.setHtml(embed_html)
                else:
                    # Nhúng trình phát MP4 HTML5
                    embed_html = f"""
                    <body style="margin:0; background-color:black; display:flex; justify-content:center; align-items:center;">
                        <video width="100%" height="100%" controls autoplay>
                            <source src="{url}" type="video/mp4">
                        </video>
                    </body>
                    """
                    self.video_player.setHtml(embed_html)
        else:
            # Nếu là Ảnh -> Dừng video đang phát, bật ShimmerLabel tải ảnh
            self.stop_video()
            self.media_stack.setCurrentIndex(0)
            self.load_main_image(url)

    def load_image_async(self, url):
        self.lbl_thumbnail.start_shimmer()

    def on_back_clicked(self):
        self.stop_video()
        self.back_requested.emit()

    def load_main_image(self, url):
        self.lbl_main_image.start_shimmer()
        if not url.startswith("http"):
            full_path = os.path.join(self.base_dir, url)
            if os.path.exists(full_path):
                self.lbl_main_image.stop_shimmer()
                self._set_main_pixmap(QPixmap(full_path))
            return

        self.downloader = ImageDownloader(url, self)
        self.downloader.data_downloaded.connect(self.on_main_image_downloaded)
        self.downloader.start()

    def on_image_downloaded(self, data, url):
        if url != self.current_media_url:
            return

    def _set_main_pixmap(self, pixmap):
        self.lbl_main_image.setPixmap(
            pixmap.scaled(self.lbl_main_image.width(), self.lbl_main_image.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        )

    def update_action_button_ui(self):
        styles = {
            "Play": ("CHƠI NGAY", "#27ae60", "#2ecc71"),
            "Update": ("CẬP NHẬT", "#f39c12", "#f1c40f"),
            "Install": ("CÀI ĐẶT", "#ff4d4d", "#ff6666")
        }
        text, bg, hover = styles.get(self.current_status, styles["Install"])
        self.detail_btn_action.setText(text)
        self.detail_btn_action.setStyleSheet(f"""
            QPushButton {{ background-color: {bg}; color: white; font-size: 18px; font-weight: bold; border-radius: 5px; border: none; }}
            QPushButton:hover {{ background-color: {hover}; }}
        """)

    def open_external_link(self, url):
        if url and isinstance(url, str) and url.strip():
            QDesktopServices.openUrl(QUrl(url.strip()))