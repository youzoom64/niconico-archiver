import tkinter as tk
from tkinter import messagebox
import threading

class BaseDialog:
    """ダイアログの基底クラス"""
    def __init__(self, parent, title, geometry="600x400"):
        self.result = None
        self.nickname_fetching = False
        self.nickname_fetch_thread = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(geometry)
        self.dialog.grab_set()
        self.dialog.transient(parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_clicked)
    
    def wait_for_result(self):
        """ダイアログの結果を待機"""
        self.dialog.wait_window()
        return self.result
    
    def cancel_clicked(self):
        """キャンセルボタンの処理"""
        self.result = None
        self.dialog.destroy()
    
    def fetch_nickname_async(self, user_id, force=False, callback=None):
        """非同期でニックネーム取得（共通処理）"""
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
                nickname = get_user_nickname_with_cache(user_id)
                
                if callback:
                    self.dialog.after(0, lambda: callback(nickname, user_id, force))
                
            except Exception as e:
                print(f"ニックネーム取得エラー (ID: {user_id}): {e}")
                if force:
                    self.dialog.after(0, lambda: messagebox.showerror(
                        "エラー", f"ニックネーム取得に失敗しました: {e}"))
            finally:
                self.nickname_fetching = False
        
        self.nickname_fetch_thread = threading.Thread(target=fetch_thread, daemon=True)
        self.nickname_fetch_thread.start()