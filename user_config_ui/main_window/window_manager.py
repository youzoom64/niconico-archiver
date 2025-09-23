import tkinter as tk
from tkinter import messagebox
from ..utils import UIUtils
from ..config_forms import ConfigForms
from ..special_users import SpecialUsersManager
from .config_vars import ConfigVarsManager
from .user_list import UserListManager
from .config_sections import ConfigSectionsManager
from .config_loader import ConfigLoader
from .config_builder import ConfigBuilder
import threading

class WindowManager:
    """ウィンドウ全体の管理"""
    
    def __init__(self, parent, config_manager, refresh_callback):
        self.config_manager = config_manager
        self.refresh_callback = refresh_callback
        
        # ニックネーム取得の重複実行を防ぐフラグ
        self.nickname_fetching = False
        self.nickname_fetch_thread = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("ユーザー設定管理")
        self.window.geometry("900x700")
        self.window.grab_set()
        
        self.current_config = None
        self.current_account_id = None
        
        # マネージャーの初期化
        self.config_vars_manager = ConfigVarsManager(self.fetch_nickname)
        self.config_vars = self.config_vars_manager.get_all()
        
        self.setup_ui()
        self.setup_callbacks()
        
        # 初期データ読み込み
        self.user_list_manager.load_users()
    
    def setup_ui(self):
        """UI設定"""
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側：ユーザー一覧
        self.user_list_manager = UserListManager(
            main_frame, self.config_manager, self.on_user_select)
        
        # ユーザー一覧のCRUD操作を設定
        self.user_list_manager.create_user = self.create_user
        self.user_list_manager.copy_user = self.copy_user
        self.user_list_manager.delete_user = self.delete_user
        
        # 右側：設定詳細
        self.setup_config_detail(main_frame)
    
    def setup_config_detail(self, parent):
        """設定詳細セクションを設定"""
        right_frame = tk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # スクロール可能フレーム
        scrollable_frame = UIUtils.create_scrollable_frame(right_frame)
        
        tk.Label(scrollable_frame, text="設定詳細", font=("", 12, "bold")).pack()
        
        # 設定フォームの作成
        self.config_forms = ConfigForms(scrollable_frame)
        self.special_users_manager = SpecialUsersManager(scrollable_frame, self.config_vars)
        self.config_sections = ConfigSectionsManager(scrollable_frame, self.config_vars_manager)
        
        # 各セクションの作成
        self.config_sections.create_display_name_section()
        self.config_forms.create_basic_settings(self.config_vars)
        self.config_forms.create_api_settings(self.config_vars)
        self.config_forms.create_audio_settings(self.config_vars)
        self.config_sections.create_music_settings()
        self.config_sections.create_prompt_settings()
        self.config_sections.create_character_settings()
        self.config_sections.create_ai_features()
        self.config_sections.create_display_features()
        self.special_users_manager.create_special_users_section()
        self.special_users_manager.create_special_users_detail_section()
        self.config_sections.create_tag_settings()
        self.config_sections.create_server_settings()
        self.create_buttons(scrollable_frame)

        
        # ウィジェット参照を取得
        widgets = {
            'tags_listbox': self.config_sections.get_widget('tags_listbox')
        }
        
        # 設定ローダーの初期化
        self.config_loader = ConfigLoader(
            self.config_manager, self.config_vars_manager, 
            self.special_users_manager, widgets)

        # ConfigBuilderを初期化（special_users_manager作成後）
        self.config_builder = ConfigBuilder(self.config_vars, self.special_users_manager)
    
    def setup_callbacks(self):
        """コールバックを設定"""
        # アカウントID変更時の処理をバインド
        self.config_vars_manager.set_trace('account_var', self.on_account_id_trace)
    
    def create_buttons(self, parent):
        """保存・キャンセルボタンを作成"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="適用", command=self.apply_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def on_user_select(self, account_id):
        """ユーザー選択時のコールバック"""
        self.current_config = self.config_loader.load_user_config(account_id)
        self.current_account_id = account_id
    
    def fetch_nickname(self):
        """ニックネーム取得ボタンのコールバック"""
        account_id = self.config_vars['account_var'].get().strip()
        if not account_id:
            messagebox.showwarning("警告", "アカウントIDを入力してください")
            return
        
        if not account_id.isdigit():
            messagebox.showwarning("警告", "正しいアカウントIDを入力してください")
            return
        
        self.fetch_nickname_async(account_id, force=True)
    
    def on_account_id_trace(self, *args):
        """アカウントIDが変更されたときの処理"""
        account_id = self.config_vars['account_var'].get().strip()
        if account_id and account_id.isdigit():
            if hasattr(self, 'nickname_timer'):
                self.window.after_cancel(self.nickname_timer)
            self.nickname_timer = self.window.after(1000, lambda: self.fetch_nickname_async(account_id, force=False))
    
    def fetch_nickname_async(self, account_id, force=False):
        """非同期でニックネームを取得"""
        if self.nickname_fetching and not force:
            return
        
        if (hasattr(self, 'nickname_fetch_thread') and 
            self.nickname_fetch_thread and 
            self.nickname_fetch_thread.is_alive() and not force):
            return
        
        self.nickname_fetching = True
        
        def fetch_thread():
            try:
                from utils import get_user_nickname_with_cache
                nickname = get_user_nickname_with_cache(account_id)
                
                self.window.after(0, lambda: self.update_display_name_safe(nickname, account_id, force))
                
            except Exception as e:
                print(f"ニックネーム取得エラー (ID: {account_id}): {e}")
                if force:
                    self.window.after(0, lambda: messagebox.showerror("エラー", f"ニックネーム取得に失敗しました: {e}"))
            finally:
                self.nickname_fetching = False
        
        self.nickname_fetch_thread = threading.Thread(target=fetch_thread, daemon=True)
        self.nickname_fetch_thread.start()
    
    def update_display_name_safe(self, nickname, account_id, force=False):
        """安全にニックネームで表示名を更新"""
        current_account_id = self.config_vars['account_var'].get().strip()
        if current_account_id != account_id:
            return
        
        if nickname:
            current_display_name = self.config_vars['display_name_var'].get().strip()
            if not current_display_name:
                self.config_vars['display_name_var'].set(nickname)
                if force:
                    messagebox.showinfo("成功", f"ニックネーム「{nickname}」を取得しました")
            elif force:
                if messagebox.askyesno("確認", f"取得したニックネーム「{nickname}」で表示名を更新しますか？\n現在の表示名: {current_display_name}"):
                    self.config_vars['display_name_var'].set(nickname)
        elif force:
            messagebox.showwarning("警告", "ニックネームを取得できませんでした")
    
    def create_user(self):
        """新規ユーザー作成"""
        account_id = self.config_vars['account_var'].get().strip()
        
        if not account_id:
            messagebox.showerror("エラー", "アカウントIDを入力してください")
            return
            
        if account_id in self.config_manager.get_user_list():
            messagebox.showerror("エラー", f"アカウントID '{account_id}' は既に存在します")
            return
        
        config = self.get_current_config()
        self.config_manager.save_user_config(account_id, config)
        self.user_list_manager.load_users()
        
        messagebox.showinfo("作成完了", f"アカウント '{account_id}' を作成しました")
    
    def copy_user(self):
        """ユーザー複製"""
        source_account_id = self.user_list_manager.get_selected_account_id()
        if not source_account_id:
            messagebox.showerror("エラー", "複製元のアカウントを選択してください")
            return
            
        new_account_id = self.config_vars['account_var'].get().strip()
        if not new_account_id:
            messagebox.showerror("エラー", "新しいアカウントIDを入力してください")
            return
            
        if new_account_id in self.config_manager.get_user_list():
            messagebox.showerror("エラー", f"アカウントID '{new_account_id}' は既に存在します")
            return
        
        if self.config_manager.copy_user_config(source_account_id, new_account_id):
            self.user_list_manager.load_users()
            messagebox.showinfo("複製完了", f"'{source_account_id}' から '{new_account_id}' を作成しました")
        else:
            messagebox.showerror("エラー", "複製に失敗しました")
    
    def delete_user(self):
        """ユーザー削除"""
        account_id = self.user_list_manager.get_selected_account_id()
        if not account_id:
            messagebox.showerror("エラー", "削除するアカウントを選択してください")
            return
        
        if messagebox.askyesno("削除確認", f"アカウント {account_id} を削除しますか？"):
            if self.config_manager.delete_user(account_id):
                self.user_list_manager.load_users()
                messagebox.showinfo("削除完了", f"アカウント {account_id} を削除しました")
            else:
                messagebox.showerror("エラー", "削除に失敗しました")
    
    def get_current_config(self):
        """現在の設定を取得"""
        return self.config_builder.build_config()
    
    def save_config(self):
        """設定を保存"""
        config = self.get_current_config()
        account_id = config["account_id"]
        
        if account_id:
            self.config_manager.save_user_config(account_id, config)
            self.user_list_manager.load_users()
            self.refresh_callback()
            messagebox.showinfo("保存完了", f"アカウント {account_id} の設定を保存しました")
        else:
            messagebox.showerror("エラー", "アカウントIDを入力してください")
    
    def apply_config(self):
        """設定を適用"""
        self.save_config()