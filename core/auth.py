# core/auth.py

import json
import hashlib
import os

# Cấu hình đường dẫn tương đối để file exe chạy ở đâu cũng đọc được
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')
USERS_DB_PATH = os.path.join(BASE_DIR, 'config', 'users.json')
# Đường dẫn lưu phiên đăng nhập
SESSION_PATH = os.path.join(BASE_DIR, 'config', 'session.json') 

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
        "password": hash_password(password),
        "is_verified": False  # [MỚI] Mặc định tài khoản mới đăng ký chưa được verify
    }
    
    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)
        
    return True, "Đăng ký thành công!"

def login_user(username, password):
    """
    Kiểm tra đăng nhập. 
    Trả về tuple: (Thành công, Có phải Admin không, Có phải Verified không, Thông báo)
    """
    if not os.path.exists(USERS_DB_PATH):
        return False, False, False, "Hệ thống chưa có tài khoản nào."
        
    with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    if username not in users:
        return False, False, False, "Sai tài khoản hoặc mật khẩu."
        
    user_data = users[username]
    if user_data['password'] == hash_password(password):
        # Đối chiếu email user với admin_email trong config
        is_admin = (user_data['email'] == get_admin_email())
        # [MỚI] Đọc trạng thái verified từ DB, nếu không có thì mặc định là False
        is_verified = user_data.get('is_verified', False)
        return True, is_admin, is_verified, "Đăng nhập thành công!"
        
    return False, False, False, "Sai tài khoản hoặc mật khẩu."

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

# ================= CÁC HÀM XỬ LÝ SESSION (KEEP ME LOGGED IN) =================

# [CẬP NHẬT] Thêm tham số is_verified vào hàm lưu session
def save_session(username, is_admin, is_verified):
    """Lưu phiên đăng nhập hiện tại vào file JSON"""
    session_data = {
        "username": username,
        "is_admin": is_admin,
        "is_verified": is_verified
    }
    # Đảm bảo thư mục config tồn tại
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    with open(SESSION_PATH, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=4)

def get_current_session():
    """Kiểm tra và trả về thông tin đăng nhập cũ nếu có"""
    if os.path.exists(SESSION_PATH):
        try:
            with open(SESSION_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def clear_session():
    """Đăng xuất: Xóa file lưu trữ phiên đăng nhập"""
    if os.path.exists(SESSION_PATH):
        try:
            os.remove(SESSION_PATH)
        except Exception:
            pass

def change_db_username(old_username, new_username):
    """
    Đổi tên user trong users.json và cập nhật session.
    Trả về tuple: (Thành công/Thất bại, Thông báo)
    """
    if not os.path.exists(USERS_DB_PATH):
        return False, "Không tìm thấy cơ sở dữ liệu người dùng."
        
    with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
        users = json.load(f)
        
    if old_username not in users:
        return False, "Tài khoản hiện tại không tồn tại trong hệ thống."
        
    if new_username in users:
        return False, "Tên đăng nhập mới đã có người sử dụng. Vui lòng chọn tên khác."
        
    # Chuyển dữ liệu từ key cũ sang key mới và xóa key cũ
    users[new_username] = users.pop(old_username)
    
    with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4)
        
    # Cập nhật lại session.json nếu user đang đổi tên chính là user đang đăng nhập
    current_session = get_current_session()
    if current_session and current_session.get("username") == old_username:
        save_session(
            new_username, 
            current_session.get("is_admin", False), 
            current_session.get("is_verified", False) # [CẬP NHẬT] Bảo toàn trạng thái verified khi đổi tên
        )
        
    return True, "Đổi tên thành công!"