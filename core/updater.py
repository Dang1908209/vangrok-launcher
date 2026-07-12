import os
import sys
import json
import requests
import zipfile
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

# ==========================================
# CẤU HÌNH GITHUB (Thay bằng repo của bạn)
# ==========================================
# Link raw tới config.json để check version
GITHUB_CONFIG_URL = "https://raw.githubusercontent.com/<ten-user>/<ten-repo>/main/config/config.json"
# Link tải nguyên cục code nhánh main dạng ZIP
GITHUB_ZIP_URL = "https://github.com/<ten-user>/<ten-repo>/archive/refs/heads/main.zip"

def check_launcher_update():
    """Kiểm tra xem có bản update Launcher mới không"""
    local_version = "1.0.0"
    local_config_path = "config/config.json"
    
    # 1. Đọc version ở máy client
    if os.path.exists(local_config_path):
        with open(local_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            local_version = config.get("version", "1.0.0")
            
    try:
        # 2. Đọc version trên GitHub
        response = requests.get(GITHUB_CONFIG_URL, timeout=5)
        if response.status_code == 200:
            remote_config = response.json()
            remote_version = remote_config.get("version", "1.0.0")
            
            # 3. So sánh (VD: "1.0.1" > "1.0.0")
            if remote_version > local_version:
                return True, remote_version
    except Exception as e:
        print(f"Lỗi check update Launcher: {e}")
        
    return False, local_version


class LauncherUpdaterWorker(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            temp_zip = "launcher_update.zip"
            extract_dir = "update_temp"

            # --- 1. Tải bản cập nhật ---
            self.status_signal.emit("Đang tải bản cập nhật Launcher...")
            response = requests.get(GITHUB_ZIP_URL, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            with open(temp_zip, 'wb') as file:
                downloaded = 0
                for data in response.iter_content(chunk_size=1024*512):
                    file.write(data)
                    downloaded += len(data)
                    # GitHub API zip đôi khi không trả về total_size, nên bỏ qua % nếu total_size = 0
                    if total_size > 0:
                        self.progress_signal.emit(int((downloaded / total_size) * 100))

            # --- 2. Giải nén ---
            self.status_signal.emit("Đang chuẩn bị dữ liệu...")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            os.remove(temp_zip)

            # Thư mục gốc khi giải nén từ GitHub thường có chữ -main (VD: vangrok-launcher-main)
            extracted_folders = os.listdir(extract_dir)
            inner_folder = os.path.join(extract_dir, extracted_folders[0])

            # --- 3. Tạo script .bat để chép đè và tự reset ---
            # Dùng file .bat để Launcher tự tắt đi, chép đè file mới, rồi bật lại. 
            # Dùng lệnh xcopy nhưng BỎ QUA thư mục installed_games để không xóa mất game của người dùng.
            bat_path = "apply_update.bat"
            bat_content = f"""@echo off
echo Đang cập nhật Vangrok Launcher... Vui lòng không đóng cửa sổ này.
timeout /t 2 /nobreak >nul

:: Chép đè toàn bộ file mới vào thư mục hiện tại (Y: Yes, E: Subfolder, Q: Quiet)
xcopy /Y /E /Q "{inner_folder}\\*" "%cd%\\"

:: Dọn dẹp thư mục tạm
rmdir /S /Q "{extract_dir}"

:: Khởi động lại Launcher
start python main.py

:: Tự xóa file bat này
del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            self.finished_signal.emit(True, "Tải hoàn tất! Launcher sẽ khởi động lại ngay bây giờ.")

            # Kích hoạt script .bat (Nó sẽ tự chạy ngầm)
            subprocess.Popen("apply_update.bat", shell=True)

        except Exception as e:
            self.finished_signal.emit(False, f"Lỗi cập nhật: {str(e)}")