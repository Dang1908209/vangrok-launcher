from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, 
                             QGridLayout, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.widgets.game_card import GameCard

class SearchPage(QWidget):
    # Tín hiệu phát ra khi người dùng click vào một game để xem chi tiết
    game_detail_requested = pyqtSignal(dict)

    def __init__(self, games_data, parent=None):
        super().__init__(parent)
        self.games_data = games_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)

        # 1. Tiêu đề trang
        lbl_title = QLabel("TÌM KIẾM TRÒ CHƠI")
        lbl_title.setStyleSheet("font-size: 32px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(lbl_title)

        # 2. Thanh tìm kiếm
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_bar")
        self.search_input.setPlaceholderText("🔍 bạn muốn tìm gì?...")
        # Lắng nghe sự kiện khi người dùng gõ phím
        self.search_input.textChanged.connect(self.filter_games)
        layout.addWidget(self.search_input)

        # 3. Vùng chứa kết quả (Hỗ trợ cuộn nếu có nhiều game)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        
        self.results_layout = QGridLayout(self.scroll_content)
        self.results_layout.setSpacing(20)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        # Hiển thị tất cả game ở lần tải đầu tiên
        self.filter_games("")

    def filter_games(self, query):
        """Hàm lọc và hiển thị lại các GameCard dựa trên từ khóa."""
        # Xóa các kết quả cũ trên màn hình
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Chuẩn hóa từ khóa tìm kiếm (chữ thường, xóa khoảng trắng thừa)
        query = query.lower().strip()
        
        # Lọc danh sách game
        if query:
            filtered_games = [
                game for game in self.games_data 
                if query in game.get("name", "").lower()
            ]
        else:
            filtered_games = self.games_data 

        # Xử lý khi không tìm thấy game nào
        if not filtered_games:
            lbl_empty = QLabel("Không tìm thấy trò chơi nào.")
            lbl_empty.setStyleSheet("color: #aaaaaa; font-size: 16px; font-style: italic;")
            self.results_layout.addWidget(lbl_empty, 0, 0)
            return

        # Hiển thị các game đã được lọc ra dạng lưới (Grid)
        row, col = 0, 0
        max_cols = 4  # Số cột tối đa trên 1 hàng (Có thể chỉnh sửa)
        
        for game in filtered_games:
            card = GameCard(game)
            # Kết nối tín hiệu click của card với tín hiệu của page để truyền lên MainWindow
            card.card_clicked.connect(self.game_detail_requested.emit)
            self.results_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1