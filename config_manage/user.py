from .base import BaseManager
from .defaults import DefaultConfigProvider
from .utils import ConfigUtils
import os

class UserManager(BaseManager):
    def __init__(self):
        super().__init__()
        self._ensure_default_config()
    
    def _ensure_default_config(self):
        """デフォルト設定を作成"""
        if not self.file_exists(self.get_user_config_path("default")):
            self.create_default_config()
    
    def create_default_config(self):
        """デフォルト設定を作成"""
        default_config = DefaultConfigProvider.get_template()
        default_config["account_id"] = "default"
        default_config["display_name"] = "デフォルト設定"
        default_config["basic_settings"]["account_id"] = "default"
        self.save_config("default", default_config)
    
    def save_config(self, account_id, config):
        """ユーザー設定を保存"""
        config_path = self.get_user_config_path(account_id)
        self.save_json(config_path, config)
    
    def load_config(self, account_id):
        """ユーザー設定を読み込み"""
        config_path = self.get_user_config_path(account_id)
        loaded_config = self.load_json(config_path)
        
        if loaded_config is None:
            if account_id == "default":
                print("デフォルト設定ファイルが見つかりません。新規作成します。")
                default_config = DefaultConfigProvider.get_template()
                self.save_config("default", default_config)
                return default_config
            else:
                print(f"設定ファイルが見つかりません: {account_id}")
                print("デフォルト設定をベースに初期化します")
                default_config = self.load_config("default")
                default_config["account_id"] = account_id
                default_config["basic_settings"]["account_id"] = account_id
                default_config["display_name"] = ""
                return default_config
        
        # デフォルト設定とマージして不足項目を補完
        default_template = DefaultConfigProvider.get_template()
        merged_config = ConfigUtils.merge_config_deep(default_template, loaded_config)
        
        print(f"設定ファイル読み込み成功: {account_id}")
        return merged_config
    
    def get_user_list(self):
        """ユーザーリストを取得"""
        if not os.path.exists(self.users_dir):
            return ["default"]
        
        account_ids = []
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                account_id = filename[:-5]
                account_ids.append(account_id)
        
        return sorted(account_ids)
    
    def get_display_info(self):
        """ユーザー表示情報を取得"""
        user_info = []
        for account_id in self.get_user_list():
            config = self.load_config(account_id)
            display_name = config.get("display_name", "")
            platform = config["basic_settings"]["platform"]
            
            label = f"{account_id} ({display_name})" if display_name else account_id
            
            user_info.append({
                "account_id": account_id,
                "display_name": display_name,
                "platform": platform,
                "label": label
            })
        
        return user_info
    
    def delete_user(self, account_id):
        """ユーザー設定を削除"""
        if account_id == "default":
            return False
        
        config_path = self.get_user_config_path(account_id)
        if self.file_exists(config_path):
            os.remove(config_path)
            return True
        return False
    
    def user_exists(self, account_id):
        """ユーザー存在チェック"""
        return self.file_exists(self.get_user_config_path(account_id))
    
    def copy_config(self, source_account_id, target_account_id):
        """ユーザー設定を複製"""
        if self.user_exists(source_account_id) and not self.user_exists(target_account_id):
            config = self.load_config(source_account_id)
            config["account_id"] = target_account_id
            config["basic_settings"]["account_id"] = target_account_id
            self.save_config(target_account_id, config)
            return True
        return False
    
    def save_current_users(self, active_users):
        """現在監視中のユーザーリストを保存"""
        data = {
            "active_users": active_users
        }
        self.save_json(self.current_users_file, data)
    
    def load_current_users(self):
        """現在監視中のユーザーリストを読み込み"""
        data = self.load_json(self.current_users_file)
        return data.get("active_users", []) if data else []