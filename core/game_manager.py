import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_DB_PATH = os.path.join(BASE_DIR, 'config', 'games.json')
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')

def get_all_games():
    """Đọc và trả về danh sách game từ file JSON."""
    if not os.path.exists(GAMES_DB_PATH):
        os.makedirs(os.path.dirname(GAMES_DB_PATH), exist_ok=True)
        with open(GAMES_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
        
    with open(GAMES_DB_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def add_game_to_db(new_game_data):
    """Thêm một game mới vào file JSON"""
    games = get_all_games()
    games.append(new_game_data)
    
    with open(GAMES_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=4, ensure_ascii=False)
        
    return True, "Đã thêm trò chơi thành công!"

# ================= CÁC HÀM XỬ LÝ SETTING & Ổ ĐĨA THẬT =================

def get_install_path():
    """Đọc đường dẫn cài đặt game từ config.json"""
    default_path = os.path.join(BASE_DIR, "installed_games")
    if not os.path.exists(CONFIG_PATH):
        return default_path
        
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Lấy key local_games_directory từ config.json của bạn
            path = data.get("local_games_directory", default_path)
            # Chuyển đổi thành đường dẫn tuyệt đối nếu đang dùng ./
            if path.startswith("."):
                path = os.path.abspath(os.path.join(BASE_DIR, path))
            return path
    except Exception:
        return default_path

def save_install_path(new_path):
    """Lưu đường dẫn cài đặt mới vào config.json"""
    data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
            
    data["local_games_directory"] = new_path
    
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    return True

def get_storage_info(path):
    """Lấy thông tin dung lượng thật của ổ đĩa chứa thư mục đó (GB)"""
    try:
        # Nếu thư mục chưa tồn tại thì tự động tạo để OS không báo lỗi ổ đĩa
        os.makedirs(path, exist_ok=True)
        total, used, free = shutil.disk_usage(path)
        
        # Chuyển từ Bytes sang Gigabytes (1 GB = 2^30 bytes)
        total_gb = max(1, total // (2**30)) 
        used_gb = used // (2**30)
        free_gb = free // (2**30)
        
        return total_gb, used_gb, free_gb
    except Exception as e:
        print(f"Lỗi đọc dung lượng ổ đĩa {path}: {e}")
        return 100, 0, 100 # Giá trị ảo phòng hờ lỗi quyền truy cập