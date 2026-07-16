import os
import sys
import json
import time
import requests
import zipfile
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

# ==========================================
# CẤU HÌNH GITHUB 
# ==========================================
# Link raw tới config.json để check version VÀ lấy link tải update
GITHUB_CONFIG_URL = "https://raw.githubusercontent.com/Dang1908209/vangrok-launcher/main/config/config.json"

def check_launcher_update():
    """Kiểm tra xem có bản update Launcher mới không"""
    # Lấy đường dẫn tuyệt đối đến thư mục chứa file .exe (hoặc file .py)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    local_config_path = os.path.join(base_dir, "config", "config.json")
    local_version = "1.0.0"
    
    # Ghi log ra file để debug (vì print() trong .exe bị ẩn)
    log_file = os.path.join(base_dir, "update_debug.log")
    
    def write_log(msg):
        try:
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(msg + "\n")
        except Exception:
            pass

    write_log(f"--- BẮT ĐẦU CHECK UPDATE ---")
    write_log(f"Đường dẫn config local: {local_config_path}")

    # 1. Đọc version ở máy client
    if os.path.exists(local_config_path):
        try:
            with open(local_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                local_version = config.get("launcher_version", "1.0.0")
                write_log(f"Tìm thấy config local. Version hiện tại: {local_version}")
        except Exception as e:
            write_log(f"Lỗi đọc config local: {e}")
    else:
        write_log(f"KHÔNG tìm thấy config local! Dùng bản mặc định: {local_version}")
        
    try:
        # 2. Đọc version trên GitHub (Thêm ?t=timestamp để PHÁ CACHE GITHUB RAW)
        url_no_cache = f"{GITHUB_CONFIG_URL}?t={int(time.time())}"
        write_log(f"Đang gọi tới GitHub: {url_no_cache}")
        
        # Thêm verify=False để chống lỗi SSL khi đóng gói thành file .exe
        response = requests.get(url_no_cache, timeout=5, verify=False)
        write_log(f"Phản hồi từ GitHub: Status Code {response.status_code}")
        
        if response.status_code == 200:
            remote_config = response.json()
            remote_version = remote_config.get("launcher_version", "1.0.0")
            write_log(f"Version trên GitHub: {remote_version}")
            
            # 3. So sánh
            if remote_version > local_version:
                write_log(f"Phát hiện bản mới! {remote_version} > {local_version}")
                return True, remote_version
            else:
                write_log(f"Không có bản mới. {remote_version} <= {local_version}")
        else:
            write_log(f"Yêu cầu thất bại, mã lỗi: {response.status_code}")
            
    except Exception as e:
        write_log(f"Lỗi kết nối GitHub: {e}")
        
    return False, local_version


class LauncherUpdaterWorker(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            temp_zip = "launcher_update.zip"
            extract_dir = "update_temp"

            # --- 0. Lấy link tải từ config.json trên GitHub ---
            self.status_signal.emit("Đang đọc thông tin bản cập nhật...")
            url_no_cache = f"{GITHUB_CONFIG_URL}?t={int(time.time())}"
            config_resp = requests.get(url_no_cache, timeout=5, verify=False)
            config_resp.raise_for_status()
            remote_config = config_resp.json()
            
            # Lấy zip_url từ config, nếu không có thì dự phòng bằng nhánh main
            zip_url = remote_config.get("zip_url", "https://github.com/Dang1908209/vangrok-launcher/archive/refs/heads/main.zip")

            # --- 1. Tải bản cập nhật ---
            self.status_signal.emit("Đang tải bản cập nhật Launcher...")
            response = requests.get(zip_url, stream=True, verify=False)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            with open(temp_zip, 'wb') as file:
                downloaded = 0
                for data in response.iter_content(chunk_size=1024*512):
                    file.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        self.progress_signal.emit(int((downloaded / total_size) * 100))

            # --- 2. Giải nén ---
            self.status_signal.emit("Đang chuẩn bị dữ liệu...")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            if os.path.exists(temp_zip):
                os.remove(temp_zip)

            # --- Kiểm tra cấu trúc thư mục giải nén ---
            extracted_items = os.listdir(extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                inner_folder = os.path.join(extract_dir, extracted_items[0])
            else:
                inner_folder = extract_dir

            # --- 3. Tạo script .bat để chép đè và tự reset ---
            bat_path = "apply_update.bat"
            bat_content = f"""@echo off
echo Dang cap nhat Vangrok Launcher... Vui long khong dong cua so nay.
timeout /t 2 /nobreak >nul

:: Chép đè toàn bộ file mới vào thư mục hiện tại (Y: Yes, E: Subfolder, Q: Quiet)
xcopy /Y /E /Q "{inner_folder}\\*" "%cd%\\"

:: Dọn dẹp thư mục tạm
rmdir /S /Q "{extract_dir}"

:: Khởi động lại Launcher bằng file .exe
start "" "VangrokLauncher.exe"

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