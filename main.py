import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import json
import os
from datetime import datetime
from user_config import UserConfigWindow
from file_monitor import MultiUserMonitor
from config_manager import ConfigManager
from logger import Logger

# GPU状態チェック用
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    GPU_NAME = torch.cuda.get_device_name() if GPU_AVAILABLE else "N/A"
    CUDA_VERSION = torch.version.cuda if GPU_AVAILABLE else "N/A"
except ImportError:
    GPU_AVAILABLE = False
    GPU_NAME = "PyTorch未インストール"
    CUDA_VERSION = "N/A"

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ニコ生アーカイブ監視システム")
        self.root.geometry("800x600")
        
        self.config_manager = ConfigManager()
        self.logger = Logger()
        
        # setup_ui()を先に実行してメソッドを定義
        self.setup_ui()
        
        # その後でMultiUserMonitorを初期化
        self.watchdog = MultiUserMonitor(self.logger, self.on_error)
        
        self.load_active_users()

    def setup_ui(self):
        # ヘッダー情報
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # GPU情報表示
        gpu_status = "利用可能" if GPU_AVAILABLE else "利用不可"
        gpu_color = "green" if GPU_AVAILABLE else "red"
        
        gpu_label = tk.Label(info_frame, 
                            text=f"GPU状態: {gpu_status} ({GPU_NAME})", 
                            fg=gpu_color, font=("", 9))
        gpu_label.pack(side=tk.LEFT)
        
        # ユーザー設定管理ボタン
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="ユーザー設定管理", 
                command=self.open_user_config).pack(side=tk.LEFT)
        
        # システム情報ボタンも追加
        tk.Button(btn_frame, text="システム情報", 
                command=self.show_system_info).pack(side=tk.LEFT, padx=(10, 0))

        # 監視中ユーザー一覧
        user_frame = tk.LabelFrame(self.root, text="監視中アカウント")
        user_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.user_tree = ttk.Treeview(user_frame, columns=("display_name", "platform", "status"), height=6)
        self.user_tree.heading("#0", text="アカウントID")
        self.user_tree.heading("display_name", text="表示名")
        self.user_tree.heading("platform", text="Platform")
        self.user_tree.heading("status", text="状態")
        
        # 列幅調整
        self.user_tree.column("#0", width=120)
        self.user_tree.column("display_name", width=150)
        self.user_tree.column("platform", width=100)
        self.user_tree.column("status", width=80)
        
        self.user_tree.pack(fill=tk.X, padx=5, pady=5)
        
        # 制御ボタン
        control_frame = tk.Frame(user_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(control_frame, text="開始", command=self.start_watch).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="停止", command=self.stop_watch).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="全停止", command=self.stop_all_watch).pack(side=tk.LEFT, padx=5)
        
        # 選択中ユーザー詳細
        detail_frame = tk.LabelFrame(self.root, text="選択中アカウント詳細")
        detail_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.detail_text = tk.Text(detail_frame, height=8, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.X, padx=5, pady=5)
        
        # ログ
        log_frame = tk.LabelFrame(self.root, text="ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # イベントバインド
        self.user_tree.bind("<<TreeviewSelect>>", self.on_user_select)
        
    def open_user_config(self):
        UserConfigWindow(self.root, self.config_manager, self.refresh_users)
        
    def refresh_users(self):
        # ユーザーリストを更新
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
            
        user_info = self.config_manager.get_user_display_info()
        for info in user_info:
            account_id = info["account_id"]
            display_name = info["display_name"]
            platform = info["platform"]
            status = "監視中" if account_id in self.watchdog.active_watchers else "停止中"
            
            self.user_tree.insert("", tk.END, text=account_id,
                                values=(display_name, platform, status))
    

    def show_system_info(self):
        """システム情報を表示"""
        import platform
        
        info = f"""システム情報:
        OS: {platform.system()} {platform.release()}
        Python: {platform.python_version()}
        GPU利用可能: {GPU_AVAILABLE}
        GPU名: {GPU_NAME}
        CUDA Version: {CUDA_VERSION}

        アクティブ監視数: {len(self.watchdog.active_watchers)}
        登録ユーザー数: {len(self.config_manager.get_user_list())}
        """
        
        # 新しいウィンドウで表示
        info_window = tk.Toplevel(self.root)
        info_window.title("システム情報")
        info_window.geometry("400x300")
        
        text_widget = tk.Text(info_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, info)
        text_widget.config(state=tk.DISABLED)
        
    def on_user_select(self, event):
        selection = self.user_tree.selection()
        if selection:
            account_id = self.user_tree.item(selection[0])["text"]
            config = self.config_manager.load_user_config(account_id)
            self.show_user_detail(config)
    
    def show_user_detail(self, config):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        
        # 音声処理設定を取得（デフォルト値対応）
        audio_settings = config.get('audio_settings', {})
        use_gpu = audio_settings.get('use_gpu', True)
        whisper_model = audio_settings.get('whisper_model', 'large-v3')
        cpu_threads = audio_settings.get('cpu_threads', 8)
        
        detail = f"""アカウントID: {config['basic_settings']['account_id']}
        表示名: {config.get('display_name', '未設定')}
        Platform: {config['basic_settings']['platform']}
        監視Dir: {config['basic_settings']['platform_directory']}
        NCVDir: {config['basic_settings']['ncv_directory']}

        音声処理設定:
        GPU使用: {'○' if use_gpu else '×'}
        Whisperモデル: {whisper_model}
        CPUスレッド数: {cpu_threads}

        AI機能:
        要約テキスト: {'○' if config['ai_features']['enable_summary_text'] else '×'}
        抽象イメージ: {'○' if config['ai_features']['enable_summary_image'] else '×'}
        AI音楽: {'○' if config['ai_features']['enable_ai_music'] else '×'}
        AI会話: {'○' if config['ai_features']['enable_ai_conversation'] else '×'}

        表示機能:
        感情スコア: {'○' if config['display_features']['enable_emotion_scores'] else '×'}
        ランキング: {'○' if config['display_features']['enable_comment_ranking'] else '×'}
        単語分析: {'○' if config['display_features']['enable_word_ranking'] else '×'}
        サムネイル: {'○' if config['display_features']['enable_thumbnails'] else '×'}

        API設定:
        AIモデル: {config['api_settings'].get('ai_model', 'openai-gpt4o')}
        OpenAI API: {'設定済み' if config['api_settings'].get('openai_api_key') else '未設定'}
        Google API: {'設定済み' if config['api_settings'].get('google_api_key') else '未設定'}
        Suno API: {'設定済み' if config['api_settings'].get('suno_api_key') else '未設定'}
        Imgur API: {'設定済み' if config['api_settings'].get('imgur_api_key') else '未設定'}

        スペシャルユーザー: {len(config['special_users'])}人"""
        
        self.detail_text.insert(1.0, detail)
        self.detail_text.config(state=tk.DISABLED)
        
    def start_watch(self):
        selection = self.user_tree.selection()
        if selection:
            account_id = self.user_tree.item(selection[0])["text"]
            config = self.config_manager.load_user_config(account_id)
            
            if account_id not in self.watchdog.active_watchers:
                self.watchdog.start_user_watch(account_id, config)
                display_name = config.get('display_name', '')
                display_label = f"{account_id} ({display_name})" if display_name else account_id
                self.log_message(f"[{display_label}] 監視開始")
                self.refresh_users()
                self.save_active_users()
    
    def stop_watch(self):
        selection = self.user_tree.selection()
        if selection:
            account_id = self.user_tree.item(selection[0])["text"]
            
            if account_id in self.watchdog.active_watchers:
                config = self.config_manager.load_user_config(account_id)
                display_name = config.get('display_name', '')
                display_label = f"{account_id} ({display_name})" if display_name else account_id
                
                self.watchdog.stop_user_watch(account_id)
                self.log_message(f"[{display_label}] 監視停止")
                self.refresh_users()
                self.save_active_users()
    
    def stop_all_watch(self):
        """全ての監視を停止"""
        active_watchers = list(self.watchdog.active_watchers.keys())
        for account_id in active_watchers:
            self.watchdog.stop_user_watch(account_id)
        
        self.log_message("全ての監視を停止しました")
        self.refresh_users()
        self.save_active_users()
    
    def on_error(self, account_id, error_msg):
        config = self.config_manager.load_user_config(account_id)
        display_name = config.get('display_name', '')
        display_label = f"{account_id} ({display_name})" if display_name else account_id
        
        self.log_message(f"[{display_label}] エラー: {error_msg}")
        self.watchdog.stop_user_watch(account_id)
        self.refresh_users()
        self.save_active_users()
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        self.logger.log(message)
    
    def save_active_users(self):
        """現在アクティブなユーザーリストを保存"""
        active_users = list(self.watchdog.active_watchers.keys())
        self.config_manager.save_current_users(active_users)
    
    def load_active_users(self):
        """前回のアクティブユーザーを復元"""
        self.refresh_users()
        
        # 前回アクティブだったユーザーを自動開始
        active_users = self.config_manager.load_current_users()
        for account_id in active_users:
            if self.config_manager.user_exists(account_id):
                config = self.config_manager.load_user_config(account_id)
                self.watchdog.start_user_watch(account_id, config)
                display_name = config.get('display_name', '')
                display_label = f"{account_id} ({display_name})" if display_name else account_id
                self.log_message(f"[{display_label}] 自動監視開始")
        
        self.refresh_users()
    
    def run(self):
        # アプリケーション終了時の処理
        def on_closing():
            self.save_active_users()
            # 全ての監視を停止
            for account_id in list(self.watchdog.active_watchers.keys()):
                self.watchdog.stop_user_watch(account_id)
            self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    app = MainWindow()
    app.run()