import tkinter as tk
from tkinter import ttk, messagebox
from .tree_handler import TreeHandler
from .sync_operations import SyncOperations
from .dialog import SpecialUserConfigDialog

class SpecialUsersManager:
    """スペシャルユーザー管理のメインクラス"""
    
    def __init__(self, parent_frame, config_vars):
        self.parent = parent_frame
        self.config_vars = config_vars
        
        # 各種ハンドラーの初期化
        self.tree_handler = None
        self.sync_operations = None
    
    def create_special_users_section(self):
        """スペシャルユーザー設定セクションを作成"""
        special_frame = tk.LabelFrame(self.parent, text="スペシャルユーザー設定")
        special_frame.pack(fill=tk.X, pady=5)
        
        # テキスト入力
        tk.Label(special_frame, text="特別処理対象ユーザーID (カンマ区切り):").pack(anchor=tk.W)
        tk.Entry(special_frame, textvariable=self.config_vars['special_users_var'], 
                width=60).pack(fill=tk.X, padx=5, pady=2)
        
        # 同期ボタン
        sync_button = tk.Button(special_frame, text="↓ 個別設定に反映", 
                               command=self.sync_special_users_to_tree)
        sync_button.pack(anchor=tk.W, padx=5, pady=2)
        
        return special_frame
    
    def create_special_users_detail_section(self):
        """スペシャルユーザー詳細設定セクションを作成"""
        detail_frame = tk.LabelFrame(self.parent, text="スペシャルユーザー詳細設定")
        detail_frame.pack(fill=tk.X, pady=5)
        
        # グローバル設定
        self._create_global_settings(detail_frame)
        
        # TreeViewと操作ボタン
        self._create_tree_section(detail_frame)
        
        return detail_frame
    
    def _create_global_settings(self, parent):
        """グローバル設定を作成"""
        global_frame = tk.LabelFrame(parent, text="デフォルト設定")
        global_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # デフォルト分析有効/無効
        tk.Checkbutton(global_frame, text="デフォルトでAI分析を有効にする",
                      variable=self.config_vars['default_analysis_enabled_var']).pack(anchor=tk.W, padx=5, pady=2)
        
        # デフォルトAIモデル
        tk.Label(global_frame, text="デフォルト分析AIモデル:").pack(anchor=tk.W, padx=5)
        default_model_combo = ttk.Combobox(global_frame,
                                         textvariable=self.config_vars['default_analysis_ai_model_var'],
                                         values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                         state="readonly", width=30)
        default_model_combo.pack(anchor=tk.W, padx=5, pady=2)
        
        # デフォルト分析プロンプト
        tk.Label(global_frame, text="デフォルト分析プロンプト:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.config_vars['default_analysis_prompt_text'] = tk.Text(global_frame, height=4, wrap=tk.WORD)
        self.config_vars['default_analysis_prompt_text'].pack(fill=tk.X, padx=5, pady=2)
        
        # デフォルトテンプレート
        tk.Label(global_frame, text="デフォルトテンプレート:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        tk.Entry(global_frame, textvariable=self.config_vars['default_template_var'], 
                width=40).pack(anchor=tk.W, padx=5, pady=2)
    
    def _create_tree_section(self, parent):
        """TreeViewセクションを作成"""
        # TreeHandlerを初期化
        self.tree_handler = TreeHandler(parent)
        
        # SyncOperationsを初期化
        self.sync_operations = SyncOperations(self.tree_handler, self.config_vars)
        
        # ボタンを作成
        user_control_frame = tk.Frame(parent)
        user_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        buttons = [
            ("ユーザー追加", self.add_special_user),
            ("編集", self.edit_special_user),
            ("削除", self.remove_special_user),
            ("複製", self.copy_special_user),
            ("↑ テキストに反映", self.sync_tree_to_special_users)
        ]
        
        for text, command in buttons:
            tk.Button(user_control_frame, text=text, command=command).pack(side=tk.LEFT, padx=5)
        
        # TreeViewを作成
        self.tree_handler.create_tree()
    
    def sync_special_users_to_tree(self):
        """テキストフィールドのユーザーIDをTreeViewに同期"""
        self.sync_operations.sync_text_to_tree()
    
    def sync_tree_to_special_users(self):
        """TreeViewのユーザーIDをテキストフィールドに同期"""
        self.sync_operations.sync_tree_to_text()
    
    def add_special_user(self):
        """スペシャルユーザー追加"""
        dialog = SpecialUserConfigDialog(
            self.parent,
            None,
            self.config_vars['default_analysis_ai_model_var'].get(),
            self.config_vars['default_analysis_prompt_text'].get(1.0, tk.END).strip(),
            self.config_vars['default_template_var'].get(),
            self.config_vars['default_analysis_enabled_var'].get()
        )
        
        if dialog.result:
            self.tree_handler.add_user_to_tree(dialog.result)
    
    def edit_special_user(self):
        """選択されたスペシャルユーザーを編集"""
        selection = self.tree_handler.get_selection()
        if not selection:
            messagebox.showwarning("警告", "編集するユーザーを選択してください")
            return
        
        user_id = self.tree_handler.get_selected_user_id()
        current_config = self.tree_handler.get_user_config(user_id, self.config_vars['default_analysis_prompt_text'])
        
        dialog = SpecialUserConfigDialog(
            self.parent,
            current_config,
            self.config_vars['default_analysis_ai_model_var'].get(),
            self.config_vars['default_analysis_prompt_text'].get(1.0, tk.END).strip(),
            self.config_vars['default_template_var'].get(),
            self.config_vars['default_analysis_enabled_var'].get()
        )
        
        if dialog.result:
            self.tree_handler.update_user_in_tree(selection, dialog.result, user_id)
    
    def remove_special_user(self):
        """選択されたスペシャルユーザーを削除"""
        selection = self.tree_handler.get_selection()
        if not selection:
            messagebox.showwarning("警告", "削除するユーザーを選択してください")
            return
        
        user_id, display_name = self.tree_handler.remove_user_from_tree(selection)
        
        if messagebox.askyesno("削除確認", f"スペシャルユーザー '{user_id} ({display_name})' を削除しますか？"):
            pass  # 削除はremove_user_from_treeで実行済み
        else:
            # キャンセルされた場合は元に戻す処理が必要だが、
            # 現在の実装では削除を先に行っているので改善が必要
            pass
    
    def copy_special_user(self):
        """選択されたスペシャルユーザーを複製"""
        selection = self.tree_handler.get_selection()
        if not selection:
            messagebox.showwarning("警告", "複製するユーザーを選択してください")
            return
        
        user_id = self.tree_handler.get_selected_user_id()
        current_config = self.tree_handler.get_user_config(user_id, self.config_vars['default_analysis_prompt_text'])
        
        if current_config:
            current_config["user_id"] = ""
            current_config["display_name"] = f"{current_config['display_name']} のコピー"
            
            dialog = SpecialUserConfigDialog(
                self.parent,
                current_config,
                self.config_vars['default_analysis_ai_model_var'].get(),
                self.config_vars['default_analysis_prompt_text'].get(1.0, tk.END).strip(),
                self.config_vars['default_template_var'].get(),
                self.config_vars['default_analysis_enabled_var'].get()
            )
            
            if dialog.result:
                self.tree_handler.add_user_to_tree(dialog.result)
    
    def load_special_users_tree(self, users_config):
        """TreeViewにスペシャルユーザー設定を読み込み"""
        self.tree_handler.load_users(users_config)
    
    def get_special_users_from_tree(self):
        """TreeViewからスペシャルユーザー設定を取得"""
        return self.tree_handler.get_all_users()