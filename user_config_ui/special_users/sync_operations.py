import tkinter as tk
from tkinter import messagebox

class SyncOperations:
    """同期操作を管理"""
    
    def __init__(self, tree_handler, config_vars):
        self.tree_handler = tree_handler
        self.config_vars = config_vars
    
    def sync_text_to_tree(self):
        """テキストフィールドのユーザーIDをTreeViewに同期"""
        user_ids = [user.strip() for user in self.config_vars['special_users_var'].get().split(",") if user.strip()]
        
        # 既存のユーザーIDを取得
        existing_users = set(self.tree_handler.get_all_user_ids())
        
        added_count = 0
        for user_id in user_ids:
            if user_id not in existing_users:
                # デフォルト設定でユーザーを作成
                user_config = {
                    "user_id": user_id,
                    "display_name": f"ユーザー{user_id}",
                    "analysis_enabled": self.config_vars['default_analysis_enabled_var'].get(),
                    "analysis_ai_model": self.config_vars['default_analysis_ai_model_var'].get(),
                    "analysis_prompt": self.config_vars['default_analysis_prompt_text'].get(1.0, tk.END).strip(),
                    "template": self.config_vars['default_template_var'].get(),
                    "description": "",
                    "tags": []
                }
                
                self.tree_handler.add_user_to_tree(user_config)
                added_count += 1
        
        message = f"{added_count}件のユーザーを個別設定に追加しました" if added_count > 0 else "追加するユーザーはありませんでした"
        messagebox.showinfo("同期完了", message)
    
    def sync_tree_to_text(self):
        """TreeViewのユーザーIDをテキストフィールドに同期"""
        user_ids = self.tree_handler.get_all_user_ids()
        self.config_vars['special_users_var'].set(", ".join(user_ids))
        messagebox.showinfo("同期完了", f"{len(user_ids)}件のユーザーIDをテキストフィールドに反映しました")