import os
import json
import shutil
import subprocess
from github import Github
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLineEdit, 
                             QLabel, QFileDialog, QMessageBox, QProgressBar)
from PyQt6.QtCore import QThread, pyqtSignal

# ==========================================
# CẤU HÌNH GITHUB
# ==========================================
try:
    from token_config import GITHUB_TOKEN
except ImportError:
    GITHUB_TOKEN = ""

# ==========================================
# 1. THREAD XỬ LÝ NGẦM
# ==========================================
class UploadGameWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, game_name, game_version, game_folder, exe_name, cover_path):
        super().__init__()
        self.game_name = game_name
        self.game_version = game_version
        self.game_folder = game_folder
        self.exe_name = exe_name
        self.cover_path = cover_path

    def run(self):
        try:
            safe_name = self.game_name.replace(" ", "_").lower()
            zip_output_path = os.path.join(os.path.dirname(self.game_folder), safe_name)
            final_zip_path = f"{zip_output_path}.zip"

            self.progress_signal.emit(f"Đang nén game {self.game_name}...", 10)
            shutil.make_archive(zip_output_path, 'zip', self.game_folder)

            self.progress_signal.emit("Đang upload file Game lên GitHub Releases...", 40)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            
            release_tag = f"v_{safe_name}"
            release = repo.create_git_release(tag=release_tag, name=f"{self.game_name} {self.game_version}", message=f"Dữ liệu bản cài đặt {self.game_name} ver {self.game_version}")
            
            asset = release.upload_asset(final_zip_path)
            download_url = asset.browser_download_url

            cover_url = ""
            if self.cover_path and os.path.exists(self.cover_path):
                cover_ext = os.path.splitext(self.cover_path)[1]
                cover_filename = f"{safe_name}_cover{cover_ext}"
                os.makedirs("assets/covers", exist_ok=True)
                local_cover_path = f"assets/covers/{cover_filename}"
                shutil.copy2(self.cover_path, local_cover_path)
                cover_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/assets/covers/{cover_filename}"

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
                "version": self.game_version, # Đã thêm trường version
                "exe_path": self.exe_name,
                "cover": cover_url,
                "download_url": download_url,
                "size_mb": round(os.path.getsize(final_zip_path) / (1024 * 1024), 2)
            }
            games_data.append(new_game)

            os.makedirs("config", exist_ok=True)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(games_data, f, indent=4, ensure_ascii=False)

            os.remove(final_zip_path)

            self.progress_signal.emit("Đang đồng bộ Code lên GitHub...", 90)
            
            # =========================================================================
            # ĐOẠN SỬA DUY NHẤT: Bơm trực tiếp GITHUB_TOKEN vào lệnh Git để không bị từ chối
            # =========================================================================
            auth_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"

            # 1. Add toàn bộ thay đổi
            subprocess.run(["git", "add", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Commit thay đổi cục bộ trước (bỏ check=True để lỡ không có gì thay đổi code không bị crash)
            subprocess.run(["git", "commit", "-m", f"Auto-update: Game {self.game_name} ver {self.game_version}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Kéo thay đổi trên mạng về (nếu có) bằng URL chứa Token để không bị xung đột
            subprocess.run(["git", "pull", auth_url, "--rebase"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 4. Push thẳng lên bằng URL chứa Token & Bắt lỗi chi tiết hiển thị ra màn hình
            push_process = subprocess.run(["git", "push", auth_url], capture_output=True, text=True, encoding="utf-8")
            if push_process.returncode != 0:
                # Nếu Git vẫn báo lỗi, nó sẽ in thẳng nguyên nhân chi tiết ra Pop-up thay vì báo status 1
                raise Exception(f"Lỗi Git Push chi tiết:\n{push_process.stderr or push_process.stdout}")
            # =========================================================================

            self.progress_signal.emit("Hoàn tất!", 100)
            self.finished_signal.emit(True, "Đã thêm game và upload thành công!")

        except Exception as e:
            self.finished_signal.emit(False, str(e))


# ==========================================
# 2. DIALOG NHẬP THÔNG TIN
# ==========================================
class AddGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin: Thêm Game Mới")
        self.resize(450, 400)

        layout = QVBoxLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nhập tên Game (VD: Vangrok RPG)")
        layout.addWidget(self.name_input)

        self.ver_input = QLineEdit()
        self.ver_input.setPlaceholderText("Phiên bản (VD: 1.0.0)")
        layout.addWidget(self.ver_input)

        self.exe_input = QLineEdit()
        self.exe_input.setPlaceholderText("File khởi chạy (VD: game.exe)")
        layout.addWidget(self.exe_input)

        self.folder_path = ""
        self.btn_select_folder = QPushButton("Chọn Folder Game...")
        self.btn_select_folder.clicked.connect(self.select_folder)
        layout.addWidget(self.btn_select_folder)

        self.cover_path = ""
        self.btn_select_cover = QPushButton("Chọn Ảnh Bìa (Tùy chọn)...")
        self.btn_select_cover.clicked.connect(self.select_cover)
        layout.addWidget(self.btn_select_cover)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        layout.addWidget(self.lbl_status)

        self.btn_start = QPushButton("TIẾN HÀNH ĐÓNG GÓI & UPLOAD")
        self.btn_start.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 12px; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_process)
        layout.addWidget(self.btn_start)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa game")
        if folder:
            self.folder_path = folder
            self.btn_select_folder.setText(f"Folder: {os.path.basename(folder)}")

    def select_cover(self):
        file, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh bìa", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            self.cover_path = file
            self.btn_select_cover.setText(f"Ảnh bìa: {os.path.basename(file)}")

    def start_process(self):
        game_name = self.name_input.text().strip()
        game_ver = self.ver_input.text().strip()
        exe_name = self.exe_input.text().strip()

        if not game_name or not game_ver or not exe_name or not self.folder_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin (bao gồm cả Version)!")
            return

        self.btn_start.setEnabled(False)
        self.worker = UploadGameWorker(game_name, game_ver, self.folder_path, exe_name, self.cover_path)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.process_finished)
        self.worker.start()

    def update_progress(self, status_text, percent):
        self.lbl_status.setText(f"Trạng thái: {status_text}")
        self.progress_bar.setValue(percent)

    def process_finished(self, success, message):
        self.btn_start.setEnabled(True)
        if success:
            QMessageBox.information(self, "Thành công", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Lỗi", f"Quá trình thất bại:\n{message}")