import tkinter as tk
from tkinter import ttk

class TreeHandler:
    """TreeViewの操作を管理"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.tree = None
        self._tree_user_data = {}
        
    def create_tree(self):
        """TreeViewを作成"""
        users_frame = tk.LabelFrame(self.parent, text="個別ユーザー設定")
        users_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # TreeView
        self.tree = ttk.Treeview(users_frame,
                                columns=("display_name", "ai_model", "analysis_enabled", "template"),
                                height=8)
        
        # ヘッダー設定
        headers = [
            ("#0", "ユーザーID", 100),
            ("display_name", "表示名", 120),
            ("ai_model", "AIモデル", 120),
            ("analysis_enabled", "分析有効", 80),
            ("template", "テンプレート", 120)
        ]
        
        for col, text, width in headers:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        # スクロールバー
        tree_scrollbar = ttk.Scrollbar(users_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.pack(side="left", fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side="right", fill="y")
        
        return users_frame
    
    def add_user_to_tree(self, user_config):
        """TreeViewにユーザーを追加"""
        user_id = user_config["user_id"]
        
        self._tree_user_data[user_id] = user_config
        
        self.tree.insert("", tk.END, text=user_id,
                        values=(user_config["display_name"],
                               user_config["analysis_ai_model"],
                               "有効" if user_config["analysis_enabled"] else "無効",
                               user_config["template"]))
    
    def update_user_in_tree(self, selection, user_config, old_user_id):
        """TreeViewのユーザー情報を更新"""
        new_user_id = user_config["user_id"]
        
        # 古いIDのデータを削除（IDが変更された場合）
        if old_user_id != new_user_id and old_user_id in self._tree_user_data:
            del self._tree_user_data[old_user_id]
        
        # 新しいデータを保存
        self._tree_user_data[new_user_id] = user_config
        
        # TreeViewの表示を更新
        self.tree.item(
            selection[0],
            text=new_user_id,
            values=(
                user_config["display_name"],
                user_config["analysis_ai_model"],
                "有効" if user_config["analysis_enabled"] else "無効",
                user_config["template"]
            )
        )
    
    def remove_user_from_tree(self, selection):
        """TreeViewからユーザーを削除"""
        item = self.tree.item(selection[0])
        user_id = item["text"]
        
        self.tree.delete(selection[0])
        
        if user_id in self._tree_user_data:
            del self._tree_user_data[user_id]
        
        return user_id, item["values"][0] if item["values"] else ""
    
    def get_selected_user_id(self):
        """選択されたユーザーIDを取得"""
        selection = self.tree.selection()
        if selection:
            return self.tree.item(selection[0])["text"]
        return None
    
    def get_selection(self):
        """現在の選択を取得"""
        return self.tree.selection()
    
    def get_user_config(self, user_id, default_analysis_prompt_text):
        """ユーザー設定を取得"""
        if user_id in self._tree_user_data:
            return self._tree_user_data[user_id]
        
        # TreeViewから基本データを取得
        for item in self.tree.get_children():
            if self.tree.item(item)["text"] == user_id:
                values = self.tree.item(item)["values"]
                return {
                    "user_id": user_id,
                    "display_name": values[0] if len(values) > 0 else "",
                    "analysis_ai_model": values[1] if len(values) > 1 else "openai-gpt4o",
                    "analysis_enabled": values[2] == "有効" if len(values) > 2 else True,
                    "template": values[3] if len(values) > 3 else "user_detail.html",
                    "analysis_prompt": default_analysis_prompt_text.get(1.0, tk.END).strip(),
                    "description": "",
                    "tags": []
                }
        
        return None
    
    def load_users(self, users_config):
        """TreeViewにユーザー設定を読み込み"""
        # 既存データをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self._tree_user_data = {}
        
        # 新しいデータを読み込み
        for user_id, user_config in users_config.items():
            self._tree_user_data[user_id] = user_config.copy()
            
            self.tree.insert("", tk.END, text=user_id,
                           values=(user_config.get("display_name", ""),
                                  user_config.get("analysis_ai_model", "openai-gpt4o"),
                                  "有効" if user_config.get("analysis_enabled", True) else "無効",
                                  user_config.get("template", "user_detail.html")))
    
    def get_all_users(self):
        """すべてのユーザー設定を取得"""
        users_config = {}
        
        for item in self.tree.get_children():
            user_id = self.tree.item(item)["text"]
            
            if user_id in self._tree_user_data:
                users_config[user_id] = self._tree_user_data[user_id].copy()
        
        return users_config
    
    def get_all_user_ids(self):
        """すべてのユーザーIDを取得"""
        return [self.tree.item(item)["text"] for item in self.tree.get_children()]