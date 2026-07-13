# downloader.py
import os
import requests
import zipfile
from PyQt6.QtCore import QThread, pyqtSignal

class GameDownloader(QThread):
    progress_signal = pyqtSignal(int)       # Phát tín hiệu cập nhật phần trăm tải (%)
    finished_signal = pyqtSignal(bool, str) # Phát tín hiệu trạng thái thành công/thất bại kèm thông điệp

    def __init__(self, download_url, game_id, base_dir):
        super().__init__()
        self.download_url = download_url
        self.game_id = game_id
        self.base_dir = base_dir
        
        # Thiết lập đường dẫn đồng bộ hoàn toàn với BASE_DIR truyền qua từ UI
        self.installed_games_dir = os.path.join(self.base_dir, "installed_games")
        self.install_dir = os.path.join(self.installed_games_dir, self.game_id)
        self.zip_path = os.path.join(self.installed_games_dir, f"{self.game_id}.zip")

    def run(self):
        try:
            # Tạo thư mục installed_games tổng nếu chưa tồn tại
            os.makedirs(self.installed_games_dir, exist_ok=True)
            
            # ==========================================================
            # GIAI ĐOẠN 1: TẢI FILE TỪ SERVER (Chiếm 0% -> 90% tiến độ)
            # ==========================================================
            with requests.get(self.download_url, stream=True, timeout=15) as response:
                response.raise_for_status() # Kích hoạt Exception nếu gặp lỗi HTTP
                total_size = int(response.headers.get('content-length', 0))
                
                with open(self.zip_path, 'wb') as file:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=1024*1024): # Đọc từng đoạn 1MB
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                # Quy đổi tiến độ tải xuống vào khoảng 0% - 90%
                                percent = int((downloaded / total_size) * 90)
                                self.progress_signal.emit(min(percent, 90))

            # ==========================================================
            # GIAI ĐOẠN 2: GIẢI NÉN FILE ZIP (Chiếm 90% -> 99% tiến độ)
            # ==========================================================
            if os.path.exists(self.zip_path):
                with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                    os.makedirs(self.install_dir, exist_ok=True)
                    
                    # Lấy danh sách toàn bộ file/thư mục con bên trong cục ZIP
                    file_list = zip_ref.infolist()
                    total_files = len(file_list)
                    
                    # Giải nén từng file một để tính toán được phần trăm tiến độ
                    for idx, member in enumerate(file_list):
                        zip_ref.extract(member, self.install_dir)
                        if total_files > 0:
                            # Quy đổi tiến độ giải nén vào khoảng 90% - 99%
                            extract_percent = 90 + int(((idx + 1) / total_files) * 9)
                            self.progress_signal.emit(min(extract_percent, 99))
                
                # 3. Dọn dẹp bộ nhớ đệm (Xóa file .zip tạm sau khi giải nén xong)
                os.remove(self.zip_path)
                
                # Hoàn tất quy trình cài đặt sạch sẽ
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, "Cài đặt thành công!")
            else:
                self.finished_signal.emit(False, "Không tìm thấy file nén đã tải về.")

        except Exception as e:
            # Hủy/xóa các file tải dở hoặc file lỗi nếu tiến trình bị đứt gãy giữa chừng
            if os.path.exists(self.zip_path):
                try:
                    os.remove(self.zip_path)
                except:
                    pass
            self.finished_signal.emit(False, f"Lỗi cài đặt: {str(e)}")