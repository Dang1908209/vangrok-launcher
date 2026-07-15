import time
from PyQt6.QtCore import QThread
from pypresence import Presence

class DiscordRPCWorker(QThread):
    def __init__(self, client_id="1526826608823111750"):
        super().__init__()
        self.client_id = client_id
        self.rpc = None
        self.is_running = True
        self.current_activity = {"details": "Đang xem Cửa hàng", "state": "Sẵn sàng chiến game"}

    def update_status(self, details, state=None, large_image="logo"):
        """Hàm để MainWindow gọi khi đổi trang hoặc vào game"""
        self.current_activity["details"] = details
        if state:
            self.current_activity["state"] = state
        self.current_activity["large_image"] = large_image

    def run(self):
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            
            # Ghi nhận thời gian bắt đầu mở Launcher
            start_time = time.time()
            
            while self.is_running:
                self.rpc.update(
                    details=self.current_activity.get("details"),
                    state=self.current_activity.get("state"),
                    large_image=self.current_activity.get("large_image", "logo"),
                    start=start_time
                )
                time.sleep(15) # Discord giới hạn cập nhật trạng thái mỗi 15 giây
        except Exception as e:
            print(f"Không thể kết nối Discord RPC: {e}")

    def stop(self):
        self.is_running = False
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except:
                pass
        self.quit()