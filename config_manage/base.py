import json
import os
from datetime import datetime

class BaseManager:
    def __init__(self):
        self.config_dir = os.path.abspath("config")
        self.users_dir = os.path.join(self.config_dir, "users")
        self.current_users_file = os.path.join(self.config_dir, "current_users.json")
        self.ensure_directories()
    
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.users_dir, exist_ok=True)
    
    def save_json(self, path, data):
        """JSON保存共通処理"""
        data["last_updated"] = datetime.now().isoformat()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_json(self, path):
        """JSON読み込み共通処理"""
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON読み込みエラー ({path}): {str(e)}")
            return None
        except Exception as e:
            print(f"ファイル読み込みエラー ({path}): {str(e)}")
            return None
    
    def get_user_config_path(self, account_id):
        """ユーザー設定ファイルのパスを取得"""
        return os.path.join(self.users_dir, f"{account_id}.json")
    
    def file_exists(self, path):
        """ファイル存在チェック"""
        return os.path.exists(path)