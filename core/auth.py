import json
import hashlib
import os

# Cấu hình đường dẫn tương đối để file exe chạy ở đâu cũng đọc được
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')
USERS_DB_PATH = os.path.join(BASE_DIR, 'config', 'users.json')

def hash_password(password: str) -> str:
    """Băm mật khẩu bằng SHA-256 để không lộ mật khẩu gốc"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_admin_email() -> str:
    """Đọc email admin từ config.json"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('admin_email', '')
    except FileNotFoundError:
        return ""

def register_user(username, email, password):
    """Đăng ký tài khoản mới và lưu vào users.json"""
    users = {}
    if os.path.exists(USERS_DB_PATH):
        with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
            users = json.load(f)
            
    if username in users:
        return False, "Tài khoản đã tồn tại!"
        
    users[username] = {
        "email": email,
        "password": hash_password(password)
    }
    
    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)
        
    return True, "Đăng ký thành công!"

def login_user(username, password):
    """
    Kiểm tra đăng nhập. 
    Trả về tuple: (Thành công hay không, Có phải Admin không, Thông báo)
    """
    if not os.path.exists(USERS_DB_PATH):
        return False, False, "Hệ thống chưa có tài khoản nào."
        
    with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    if username not in users:
        return False, False, "Sai tài khoản hoặc mật khẩu."
        
    user_data = users[username]
    if user_data['password'] == hash_password(password):
        # Đối chiếu email user với admin_email trong config
        is_admin = (user_data['email'] == get_admin_email())
        return True, is_admin, "Đăng nhập thành công!"
        
    return False, False, "Sai tài khoản hoặc mật khẩu."

def reset_password(username, email, new_password):
    """
    Kiểm tra khớp username và email thì cho phép đổi mật khẩu mới.
    """
    if not os.path.exists(USERS_DB_PATH):
        return False, "Hệ thống chưa có tài khoản nào."
        
    with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    if username not in users:
        return False, "Tài khoản không tồn tại."
        
    if users[username]['email'] != email:
        return False, "Email xác minh không chính xác."
        
    # Cập nhật mật khẩu mới (đã hash)
    users[username]['password'] = hash_password(new_password)
    
    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)
        
    return True, "Khôi phục mật khẩu thành công!"