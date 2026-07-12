import requests
import json
import os

# Thay bằng link RAW tới file games.json trên repo của bạn
# VD: https://raw.githubusercontent.com/nguyenvana/vangrok-launcher/main/config/games.json
GITHUB_GAMES_JSON_URL = "https://raw.githubusercontent.com/<ten-user>/<ten-repo>/main/config/games.json"

def fetch_games_list():
    """Tải danh sách game mới nhất từ GitHub"""
    try:
        response = requests.get(GITHUB_GAMES_JSON_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Lỗi mạng khi tải danh sách game: {e}")
        # Chế độ Offline: Đọc file cục bộ nếu mất mạng
        local_config = "config/games.json"
        if os.path.exists(local_config):
            with open(local_config, "r", encoding="utf-8") as f:
                return json.load(f)
        return []