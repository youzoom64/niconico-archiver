from .base import BaseManager
from .user import UserManager
from .utils import ConfigUtils

class ArgumentsManager(BaseManager):
    def __init__(self):
        super().__init__()
        self.user_manager = UserManager()
    
    def get_arguments_config(self, account_id="default"):
        """引数設定を取得"""
        config = self.user_manager.load_config(account_id)
        return config.get("arguments_config", {}).get("enabled_arguments", {})
    
    def add_argument(self, account_id, arg_name, arg_config):
        """引数を追加"""
        # バリデーション
        is_valid, message = ConfigUtils.validate_argument_config(arg_config)
        if not is_valid:
            return False, message
        
        # 設定を読み込み
        config = self.user_manager.load_config(account_id)
        
        # arguments_configが存在しない場合は初期化
        if "arguments_config" not in config:
            config["arguments_config"] = {"enabled_arguments": {}}
        if "enabled_arguments" not in config["arguments_config"]:
            config["arguments_config"]["enabled_arguments"] = {}
        
        # 引数を追加
        config["arguments_config"]["enabled_arguments"][arg_name] = arg_config
        
        # 保存
        self.user_manager.save_config(account_id, config)
        return True, "引数を追加しました"
    
    def remove_argument(self, account_id, arg_name):
        """引数を削除"""
        config = self.user_manager.load_config(account_id)
        
        if ("arguments_config" in config and 
            "enabled_arguments" in config["arguments_config"] and
            arg_name in config["arguments_config"]["enabled_arguments"]):
            
            del config["arguments_config"]["enabled_arguments"][arg_name]
            self.user_manager.save_config(account_id, config)
            return True, "引数を削除しました"
        
        return False, "引数が見つかりません"
    
    def update_argument(self, account_id, arg_name, arg_config):
        """引数設定を更新"""
        # バリデーション
        is_valid, message = ConfigUtils.validate_argument_config(arg_config)
        if not is_valid:
            return False, message
        
        config = self.user_manager.load_config(account_id)
        
        if ("arguments_config" in config and 
            "enabled_arguments" in config["arguments_config"] and
            arg_name in config["arguments_config"]["enabled_arguments"]):
            
            config["arguments_config"]["enabled_arguments"][arg_name] = arg_config
            self.user_manager.save_config(account_id, config)
            return True, "引数設定を更新しました"
        
        return False, "引数が見つかりません"
    
    def list_arguments(self, account_id="default"):
        """引数一覧を取得"""
        return list(self.get_arguments_config(account_id).keys())