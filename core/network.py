import os
import json
import requests

# Link RAW tới file games.json trên repo của bạn
GITHUB_GAMES_JSON_URL = "https://raw.githubusercontent.com/Dang1908209/vangrok-launcher/main/config/games.json"

def sync_and_fetch_games(base_dir):
    """
    Tải danh sách game mới nhất từ GitHub, cập nhật config/games.json cục bộ
    và tự động xóa bỏ các ảnh cover không còn nằm trong danh sách game.
    """
    local_config_path = os.path.join(base_dir, "config", "games.json")
    covers_dir = os.path.join(base_dir, "assets", "covers")
    
    games_list = []
    
    # 1. THỰC HIỆN ĐỒNG BỘ (ONLINE)
    try:
        response = requests.get(GITHUB_GAMES_JSON_URL, timeout=5)
        response.raise_for_status()
        games_list = response.json()
        
        # Tạo thư mục config nếu chưa có và lưu đè file JSON mới nhất
        os.makedirs(os.path.dirname(local_config_path), exist_ok=True)
        with open(local_config_path, "w", encoding="utf-8") as f:
            json.dump(games_list, f, ensure_ascii=False, indent=4)
        print("🚀 [ONLINE] Đã đồng bộ danh sách game mới nhất từ GitHub!")
        
    # 2. XỬ LÝ KHI MẤT MẠNG (OFFLINE FALLBACK)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ [OFFLINE] Lỗi kết nối mạng ({e}). Đang đọc dữ liệu cục bộ...")
        if os.path.exists(local_config_path):
            try:
                with open(local_config_path, "r", encoding="utf-8") as f:
                    games_list = json.load(f)
                print("📂 Đã tải danh sách game offline từ bộ nhớ tạm thành công.")
            except Exception as read_err:
                print(f"❌ Lỗi đọc file config cục bộ: {read_err}")
        else:
            print("❌ Không tìm thấy dữ liệu game cục bộ nào!")

    # 3. TỰ ĐỘNG DỌN DẸP ẢNH COVER THỪA
    if games_list and os.path.exists(covers_dir):
        # Lấy danh sách tên file cover đang hoạt động từ JSON
        active_covers = set()
        for game in games_list:
            cover_url = game.get("cover", "")
            if cover_url:
                cover_filename = cover_url.split("/")[-1]
                active_covers.add(cover_filename)
        
        # Quét thư mục ảnh cục bộ và xóa những file không có trong danh sách hoạt động
        try:
            for filename in os.listdir(covers_dir):
                # Chỉ kiểm tra và dọn dẹp các định dạng ảnh phổ biến
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.ico')):
                    if filename not in active_covers:
                        file_to_delete = os.path.join(covers_dir, filename)
                        os.remove(file_to_delete)
                        print(f"🧹 Đã dọn dẹp ảnh cover thừa: {filename}")
        except Exception as clean_err:
            print(f"⚠️ Lỗi khi dọn dẹp bộ nhớ đệm ảnh: {clean_err}")

    return games_list