import os
import sys
import json
import shutil
import subprocess
import traceback  # MỚI THÊM: Để truy xuất chi tiết lỗi
from github import Github
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
                             QLabel, QFileDialog, QMessageBox, QProgressBar, QFrame, QTextEdit)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

# ==========================================
# CẤU HÌNH GITHUB
# ==========================================

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)

try:
    from token_config import GITHUB_TOKEN
except ImportError:
    GITHUB_TOKEN = ""

# Đặt tạm biến REPO_NAME nếu bạn chưa khai báo ở file khác
# Thay "Username/RepoName" bằng của bạn
REPO_NAME = "Dang1908209/vangrok-launcher" 

# ==========================================
# 1. THREAD XỬ LÝ NGẦM
# ==========================================
class UploadGameWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)  # MỚI THÊM: Bắn log ra Console

    def __init__(self, game_name, game_version, game_folder, exe_name, cover_path, video_url, description):
        super().__init__()
        self.game_name = game_name
        self.game_version = game_version
        self.game_folder = game_folder
        self.exe_name = exe_name
        self.cover_path = cover_path
        self.video_url = video_url          # Thêm biến lưu Video
        self.description = description      # Thêm biến lưu Mô tả

    def run(self):
        try:
            self.log_signal.emit(f"=== BẮT ĐẦU XỬ LÝ GAME: {self.game_name} ===")
            safe_name = self.game_name.replace(" ", "_").lower()
            zip_output_path = os.path.join(os.path.dirname(self.game_folder), safe_name)
            final_zip_path = f"{zip_output_path}.zip"

            self.log_signal.emit(f"[1/5] Đang nén thư mục: {self.game_folder}")
            self.progress_signal.emit(f"Đang nén game {self.game_name}...", 10)
            shutil.make_archive(zip_output_path, 'zip', self.game_folder)
            self.log_signal.emit(f"-> Nén thành công: {final_zip_path}")

            self.log_signal.emit(f"[2/5] Đang kết nối GitHub (Repo: {REPO_NAME})...")
            self.progress_signal.emit("Đang upload file Game lên GitHub Releases...", 40)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            
            release_tag = f"v_{safe_name}_{self.game_version.replace('.', '_')}"
            self.log_signal.emit(f"-> Tạo Release tag: {release_tag}")
            release = repo.create_git_release(
                tag=release_tag, 
                name=f"{self.game_name} {self.game_version}", 
                message=f"Dữ liệu bản cài đặt {self.game_name} ver {self.game_version}"
            )
            
            self.log_signal.emit(f"-> Bắt đầu Upload file ZIP (Bước này tốn thời gian tùy mạng)...")
            asset = release.upload_asset(final_zip_path)
            download_url = asset.browser_download_url
            self.log_signal.emit(f"-> Upload ZIP thành công! URL: {download_url}")

            cover_url = ""
            if self.cover_path and os.path.exists(self.cover_path):
                self.log_signal.emit(f"[3/5] Đang xử lý ảnh bìa...")
                cover_ext = os.path.splitext(self.cover_path)[1]
                cover_filename = f"{safe_name}_cover{cover_ext}"
                os.makedirs("assets/covers", exist_ok=True)
                local_cover_path = f"assets/covers/{cover_filename}"
                shutil.copy2(self.cover_path, local_cover_path)
                cover_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/assets/covers/{cover_filename}"
                self.log_signal.emit(f"-> Lưu ảnh bìa thành: {local_cover_path}")

            self.log_signal.emit(f"[4/5] Đang cập nhật database (games.json)...")
            self.progress_signal.emit("Đang cập nhật database (games.json)...", 80)
            json_file = "config/games.json"
            games_data = []
            if os.path.exists(json_file):
                with open(json_file, "r", encoding="utf-8") as f:
                    games_data = json.load(f)

            games_data = [g for g in games_data if g.get("id") != safe_name]

            new_game = {
                "id": safe_name,
                "name": self.game_name,
                "version": self.game_version, 
                "description": self.description,   # Lưu vào JSON
                "video_url": self.video_url,       # Lưu vào JSON
                "exe_path": self.exe_name,
                "cover": cover_url,
                "download_url": download_url,
                "size": round(os.path.getsize(final_zip_path) / (1024 * 1024), 2)
            }
            games_data.append(new_game)

            os.makedirs("config", exist_ok=True)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(games_data, f, indent=4, ensure_ascii=False)

            self.log_signal.emit("-> Dọn dẹp file ZIP tạm...")
            os.remove(final_zip_path)

            self.log_signal.emit(f"[5/5] Đang đồng bộ Source Code lên GitHub...")
            self.progress_signal.emit("Đang đồng bộ Code lên GitHub...", 90)
            
            auth_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"

            self.log_signal.emit("-> Chạy lệnh: git add .")
            subprocess.run(["git", "add", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log_signal.emit("-> Chạy lệnh: git commit")
            subprocess.run(["git", "commit", "-m", f"Auto-update: Game {self.game_name} ver {self.game_version}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log_signal.emit("-> Chạy lệnh: git pull --rebase")
            subprocess.run(["git", "pull", auth_url, "--rebase"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.log_signal.emit("-> Chạy lệnh: git push")
            push_process = subprocess.run(["git", "push", auth_url], capture_output=True, text=True, encoding="utf-8")
            if push_process.returncode != 0:
                raise Exception(f"Lỗi Git Push chi tiết:\n{push_process.stderr or push_process.stdout}")

            self.log_signal.emit("=== HOÀN TẤT THÀNH CÔNG ===")
            self.progress_signal.emit("Hoàn tất!", 100)
            self.finished_signal.emit(True, "Đã thêm game và upload thành công!")

        except Exception as e:
            error_trace = traceback.format_exc()
            self.log_signal.emit(f"\n❌ LỖI NGHIÊM TRỌNG:\n{error_trace}")
            self.finished_signal.emit(False, "Quá trình thất bại! Vui lòng đọc dòng lỗi màu đỏ bên bảng Console.")


# ==========================================
# 2. DIALOG NHẬP THÔNG TIN (GIAO DIỆN MỚI)
# ==========================================
class AddGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin: Thêm Game Mới")
        self.resize(950, 600)  # Nới rộng cửa sổ để chứa khung Mô tả
        self.folder_path = ""
        self.cover_path = ""
        
        self.setup_ui()
        self.apply_stylesheet()

    def setup_ui(self):
        master_layout = QHBoxLayout(self)
        master_layout.setContentsMargins(20, 20, 20, 20)
        master_layout.setSpacing(20)

        # ================== CỘT TRÁI (FORM) ==================
        left_widget = QFrame()
        main_layout = QVBoxLayout(left_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        lbl_title = QLabel("THÊM TRÒ CHƠI MỚI")
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl_title)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # --- Hình ảnh ---
        left_layout = QVBoxLayout()
        self.img_preview = QLabel("NO COVER")
        self.img_preview.setObjectName("img_preview")
        self.img_preview.setFixedSize(140, 200)
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_select_cover = QPushButton("🖼 Chọn Ảnh Bìa")
        self.btn_select_cover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_cover.clicked.connect(self.select_cover)
        
        left_layout.addWidget(self.img_preview)
        left_layout.addWidget(self.btn_select_cover)
        left_layout.addStretch()
        content_layout.addLayout(left_layout)

        # --- Input ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tên Game (VD: Vangrok RPG)")
        
        self.ver_input = QLineEdit()
        self.ver_input.setPlaceholderText("Không bắt buộc (Mặc định: 1.0.0)")
        
        self.exe_input = QLineEdit()
        self.exe_input.setPlaceholderText("File khởi chạy (VD: game.exe)")
        
        self.video_input = QLineEdit()
        self.video_input.setPlaceholderText("Không bắt buộc (VD: Link YouTube / .mp4)")

        self.desc_input = QTextEdit()
        self.desc_input.setObjectName("desc_input")
        self.desc_input.setPlaceholderText("Nhập mô tả về game (Không bắt buộc)...")
        self.desc_input.setMaximumHeight(70) # Hạn chế chiều cao khung mô tả
        
        # Thêm các Label và Input vào cột phải
        right_layout.addWidget(QLabel("Tên trò chơi (*):"))
        right_layout.addWidget(self.name_input)
        
        right_layout.addWidget(QLabel("Phiên bản:"))
        right_layout.addWidget(self.ver_input)
        
        right_layout.addWidget(QLabel("File thực thi (*):"))
        right_layout.addWidget(self.exe_input)
        
        right_layout.addWidget(QLabel("Link Video Trailer:"))
        right_layout.addWidget(self.video_input)

        right_layout.addWidget(QLabel("Mô tả Game:"))
        right_layout.addWidget(self.desc_input)
        
        self.folder_frame = QFrame()
        self.folder_frame.setObjectName("folder_frame")
        folder_layout = QVBoxLayout(self.folder_frame)
        folder_layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_folder_info = QLabel("📁 Chưa chọn thư mục game (*)")
        self.lbl_folder_info.setWordWrap(True)
        self.lbl_folder_info.setStyleSheet("color: #aaaaaa; font-style: italic;")
        
        self.btn_select_folder = QPushButton("📂 Duyệt Tìm Folder Game...")
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_folder.setObjectName("btn_secondary")
        self.btn_select_folder.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(self.lbl_folder_info)
        folder_layout.addWidget(self.btn_select_folder)
        
        right_layout.addWidget(self.folder_frame)
        right_layout.addStretch()
        
        content_layout.addLayout(right_layout)
        main_layout.addLayout(content_layout)

        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #cccccc; font-weight: bold;")
        main_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        main_layout.addWidget(self.progress_bar)

        self.btn_start = QPushButton("TIẾN HÀNH ĐÓNG GÓI & UPLOAD")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        main_layout.addWidget(self.btn_start)

        master_layout.addWidget(left_widget, stretch=5)


        # ================== CỘT PHẢI (CONSOLE) ==================
        right_widget = QFrame()
        console_layout = QVBoxLayout(right_widget)
        console_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_console = QLabel("💻 THÔNG TIN TIẾN TRÌNH (CONSOLE)")
        lbl_console.setObjectName("title")
        lbl_console.setAlignment(Qt.AlignmentFlag.AlignCenter)
        console_layout.addWidget(lbl_console)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setObjectName("console_output")
        self.console_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) 
        console_layout.addWidget(self.console_output)

        master_layout.addWidget(right_widget, stretch=4)


    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
            }
            QLabel {
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 5px;
            }
            QLabel#img_preview {
                background-color: #1e1e1e;
                border: 2px dashed #555555;
                color: #777777;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #444444;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #e53935;
            }
            QTextEdit#desc_input {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #444444;
                padding: 8px;
                border-radius: 4px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextEdit#desc_input:focus {
                border: 1px solid #e53935;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton#btn_secondary {
                background-color: #444444;
            }
            QPushButton#btn_secondary:hover {
                background-color: #555555;
            }
            QPushButton#btn_start {
                background-color: #28a745;
                color: white;
                font-size: 14px;
                padding: 12px;
                margin-top: 10px;
            }
            QPushButton#btn_start:hover {
                background-color: #218838;
            }
            QPushButton#btn_start:disabled {
                background-color: #555555;
                color: #888888;
            }
            QFrame#folder_frame {
                background-color: #222222;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 5px;
            }
            QProgressBar {
                background-color: #1e1e1e;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #e53935;
                border-radius: 4px;
            }
            QTextEdit#console_output {
                background-color: #0c0c0c;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px;
            }
        """)

    def get_folder_size(self, path):
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa game")
        if folder:
            self.folder_path = folder
            size_bytes = self.get_folder_size(folder)
            size_mb = size_bytes / (1024 * 1024)
            
            if size_mb > 1024:
                size_str = f"{size_mb / 1024:.2f} GB"
            else:
                size_str = f"{size_mb:.2f} MB"
                
            self.lbl_folder_info.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.lbl_folder_info.setText(f"📁 {os.path.basename(folder)}\n📦 Dung lượng: {size_str}")

    def select_cover(self):
        file, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh bìa", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.cover_path = file
            pixmap = QPixmap(file)
            self.img_preview.setPixmap(pixmap.scaled(
                self.img_preview.width(), 
                self.img_preview.height(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            ))
            self.img_preview.setStyleSheet("border: 1px solid #555;")

    def start_process(self):
        game_name = self.name_input.text().strip()
        exe_name = self.exe_input.text().strip()
        game_ver = self.ver_input.text().strip()
        video_url = self.video_input.text().strip()
        description = self.desc_input.toPlainText().strip()

        # Nếu không nhập version thì mặc định là "1.0.0"
        if not game_ver:
            game_ver = "1.0.0"

        # Bỏ đi điều kiện bắt buộc nhập version
        if not game_name or not exe_name or not self.folder_path:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập các thông tin bắt buộc (*): Tên Game, File chạy và chọn Folder!")
            return

        self.console_output.clear()
        self.btn_start.setEnabled(False)
        
        self.worker = UploadGameWorker(
            game_name, 
            game_ver, 
            self.folder_path, 
            exe_name, 
            self.cover_path,
            video_url,      # Truyền biến video
            description     # Truyền biến mô tả
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.append_log) 
        self.worker.finished_signal.connect(self.process_finished)
        self.worker.start()

    def append_log(self, text):
        self.console_output.append(text)
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, status_text, percent):
        self.lbl_status.setText(f"Trạng thái: {status_text}")
        self.progress_bar.setValue(percent)

    def process_finished(self, success, message):
        self.btn_start.setEnabled(True)
        if success:
            QMessageBox.information(self, "Thành công", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Lỗi", message)