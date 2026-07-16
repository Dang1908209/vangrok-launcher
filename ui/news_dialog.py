import requests
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt

class NewsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tin tức cập nhật - Vangrok Launcher")
        self.setFixedSize(450, 350)

        layout = QVBoxLayout()

        self.title_label = QLabel("📢 THÔNG TIN BẢN CẬP NHẬT")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #4CAF50;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Hộp văn bản hiển thị tin tức
        self.news_box = QTextEdit()
        self.news_box.setReadOnly(True) # Chỉ cho đọc, không cho người dùng gõ chữ vào
        self.news_box.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #ffffff; 
            font-size: 13px;
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(self.news_box)

        self.btn_close = QPushButton("Đóng")
        self.btn_close.setStyleSheet("padding: 8px; font-weight: bold; background-color: #2b2d31; color: white;")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

        self.setLayout(layout)
        
        # Gọi hàm lấy tin tức ngay khi mở popup
        self.fetch_news()

    def fetch_news(self):
        self.news_box.setText("Đang tải tin tức từ Vangrok Server...")
        # Lấy file news.json từ GitHub
        url = "https://raw.githubusercontent.com/Dang1908209/vangrok-launcher/main/config/news.json"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                news_data = response.json()
                content = ""
                
                # Duyệt qua từng bản update và in ra
                for item in news_data.get("updates", []):
                    content += f"[{item['date']}] - Phiên bản {item['launcher_version']}\n"
                    content += f"🔥 {item['title']}\n"
                    content += f"{item['content']}\n"
                    content += "--------------------------------------\n\n"
                    
                self.news_box.setText(content)
            else:
                self.news_box.setText("Không có thông báo mới nào.")
        except Exception as e:
            self.news_box.setText("Lỗi mạng: Không thể kết nối đến máy chủ tin tức.")