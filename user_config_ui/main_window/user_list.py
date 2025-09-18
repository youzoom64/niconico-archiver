import tkinter as tk
from tkinter import messagebox

class UserListManager:
    """ユーザー一覧の管理"""
    
    def __init__(self, parent_frame, config_manager, on_user_select_callback):
        self.parent = parent_frame
        self.config_manager = config_manager
        self.on_user_select_callback = on_user_select_callback
        self.user_listbox = None
        self.setup_ui()
    
    def setup_ui(self):
        """ユーザー一覧UIを設定"""
        left_frame = tk.Frame(self.parent)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        tk.Label(left_frame, text="アカウント一覧", font=("", 12, "bold")).pack()
        
        self.user_listbox = tk.Listbox(left_frame, width=25)
        self.user_listbox.pack(fill=tk.Y, expand=True, pady=5)
        self.user_listbox.bind("<<ListboxSelect>>", self._on_select)
        
        self._create_buttons(left_frame)
    
    def _create_buttons(self, parent):
        """ボタンを作成"""
        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=5)
        
        buttons = [
            ("新規作成", self.create_user),
            ("複製", self.copy_user),
            ("削除", self.delete_user)
        ]
        
        for text, command in buttons:
            tk.Button(btn_frame, text=text, command=command).pack(fill=tk.X, pady=2)
    
    def _on_select(self, event):
        """リスト選択時のコールバック"""
        selection = self.user_listbox.curselection()
        if selection and self.on_user_select_callback:
            selected_label = self.user_listbox.get(selection[0])
            account_id = selected_label.split(" ")[0]
            self.on_user_select_callback(account_id)
    
    def load_users(self):
        """ユーザー一覧を読み込み"""
        user_info = self.config_manager.get_user_display_info()
        self.user_listbox.delete(0, tk.END)
        for info in user_info:
            self.user_listbox.insert(tk.END, info["label"])
    
    def get_selected_account_id(self):
        """選択されたアカウントIDを取得"""
        selection = self.user_listbox.curselection()
        if selection:
            selected_label = self.user_listbox.get(selection[0])
            return selected_label.split(" ")[0]
        return None
    
    # 以下、CRUD操作はwindow_managerに委譲するためのコールバック用プレースホルダー
    def create_user(self):
        """新規作成 - 実装は親クラスに委譲"""
        pass
    
    def copy_user(self):
        """複製 - 実装は親クラスに委譲"""
        pass
    
    def delete_user(self):
        """削除 - 実装は親クラスに委譲"""
        pass