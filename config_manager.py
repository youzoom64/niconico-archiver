from config_manage import UserManager, ArgumentsManager

class ConfigManager:
    def __init__(self):
        self.user = UserManager()
        self.arguments = ArgumentsManager()
    
    # 既存メソッドをプロキシとして保持（互換性維持）
    def save_user_config(self, account_id, config):
        return self.user.save_config(account_id, config)
    
    def load_user_config(self, account_id):
        return self.user.load_config(account_id)
    
    def get_user_list(self):
        return self.user.get_user_list()
    
    def get_user_display_info(self):
        return self.user.get_display_info()
    
    def delete_user(self, account_id):
        return self.user.delete_user(account_id)
    
    def user_exists(self, account_id):
        return self.user.user_exists(account_id)
    
    def save_current_users(self, active_users):
        return self.user.save_current_users(active_users)
    
    def load_current_users(self):
        return self.user.load_current_users()
    
    def copy_user_config(self, source_account_id, target_account_id):
        return self.user.copy_config(source_account_id, target_account_id)