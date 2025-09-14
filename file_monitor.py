import os
import time
import re
import subprocess
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Mp4FileHandler(FileSystemEventHandler):
    def __init__(self, mp4_monitor):
        self.mp4_monitor = mp4_monitor
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.mp4'):
            filename = os.path.basename(event.src_path)
            print(f"DEBUG: [{self.mp4_monitor.user_name}] 新規MP4ファイル検出: {filename}")
            self.mp4_monitor.handle_new_file(filename)
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.mp4'):
            filename = os.path.basename(event.src_path)
            self.mp4_monitor.handle_file_change(filename)

class Mp4Monitor:
    def __init__(self, user_name, config, logger, error_callback):
        self.user_name = user_name
        self.config = config
        self.logger = logger
        self.error_callback = error_callback
        
        # パスを絶対パスに変換
        platform_dir = config["basic_settings"]["platform_directory"]
        if os.path.isabs(platform_dir):
            self.base_platform_directory = platform_dir
        else:
            self.base_platform_directory = os.path.abspath(platform_dir)
        
        # アカウントIDからディレクトリを特定
        self.platform_directory = self.find_account_directory()
        
        self.running = False
        self.observer = None
        self.file_sizes = {}  # ファイルサイズ記録用
        self.stability_threads = {}  # ファイル安定性確認用スレッド
        
        # 起動時の既存ファイルを無視リストに追加
        self.ignored_files = set()
        self.initialize_ignored_files()

    def initialize_ignored_files(self):
        """起動時の既存ファイルを無視リストに追加"""
        try:
            if os.path.exists(self.platform_directory):
                existing_files = self.get_mp4_files_with_size()
                self.ignored_files = set(existing_files.keys())
                if self.ignored_files:
                    print(f"DEBUG: [{self.user_name}] 既存ファイルを無視リストに追加: {list(self.ignored_files)}")
                else:
                    print(f"DEBUG: [{self.user_name}] 既存ファイルなし")
            else:
                print(f"DEBUG: [{self.user_name}] 監視ディレクトリが存在しないため、無視リストは空")
        except Exception as e:
            print(f"DEBUG: [{self.user_name}] 無視リスト初期化エラー: {str(e)}")
            self.ignored_files = set()

    def handle_new_file(self, filename):
        """新規ファイル検出時の処理"""
        if filename in self.ignored_files:
            return
        
        # 5秒後に安定性をチェックするスレッドを開始
        if filename in self.stability_threads:
            self.stability_threads[filename].cancel()
        
        self.stability_threads[filename] = threading.Timer(5.0, self.check_file_stability, [filename])
        self.stability_threads[filename].start()
        
    def handle_file_change(self, filename):
        """ファイル変更時の処理"""
        if filename in self.ignored_files:
            return
            
        # ファイルが変更されたら、既存のタイマーをキャンセルして新しいタイマーを開始
        if filename in self.stability_threads:
            self.stability_threads[filename].cancel()
        
        self.stability_threads[filename] = threading.Timer(5.0, self.check_file_stability, [filename])
        self.stability_threads[filename].start()
        print(f"DEBUG: [{self.user_name}] ファイル変更検出、安定性チェック再開: {filename}")

    def check_file_stability(self, filename):
        """ファイル安定性チェック（5秒後に実行）"""
        try:
            filepath = os.path.join(self.platform_directory, filename)
            if not os.path.exists(filepath):
                return
                
            print(f"DEBUG: [{self.user_name}] ファイル安定判定: {filename}")
            
            lv_value = self.extract_lv_value(filename)
            if lv_value:
                print(f"DEBUG: [{self.user_name}] lv値抽出成功: {lv_value}")
                self.call_pipeline(lv_value)
                # 処理完了後は無視リストに追加
                self.ignored_files.add(filename)
                print(f"DEBUG: [{self.user_name}] ファイルを無視リストに追加: {filename}")
            else:
                print(f"DEBUG: [{self.user_name}] lv値が見つかりません: {filename}")
                
            # タイマーをクリーンアップ
            if filename in self.stability_threads:
                del self.stability_threads[filename]
                
        except Exception as e:
            print(f"DEBUG: [{self.user_name}] 安定性チェックエラー: {str(e)}")

    def find_account_directory(self):
        """アカウントIDを含むディレクトリを検索"""
        try:
            account_id = self.config["basic_settings"]["account_id"]
            
            if not os.path.exists(self.base_platform_directory):
                self.logger.log(f"[{self.user_name}] 監視ディレクトリが存在しません: {self.base_platform_directory}")
                return self.base_platform_directory
            
            # ディレクトリ一覧を取得
            for dirname in os.listdir(self.base_platform_directory):
                dir_path = os.path.join(self.base_platform_directory, dirname)
                
                if os.path.isdir(dir_path):
                    # アンダースコア前の数字部分を抽出
                    if '_' in dirname:
                        id_part = dirname.split('_')[0]
                    else:
                        id_part = dirname
                    
                    # アカウントIDと一致するかチェック
                    if id_part == account_id:
                        self.logger.log(f"[{self.user_name}] アカウントディレクトリ発見: {dir_path}")
                        return dir_path
            
            # 見つからない場合は作成
            account_dir = os.path.join(self.base_platform_directory, f"{account_id}_user")
            os.makedirs(account_dir, exist_ok=True)
            self.logger.log(f"[{self.user_name}] アカウントディレクトリ作成: {account_dir}")
            return account_dir
            
        except Exception as e:
            self.logger.log(f"[{self.user_name}] ディレクトリ検索エラー: {str(e)}")
            return self.base_platform_directory

    def get_mp4_files_with_size(self):
        """MP4ファイル一覧とサイズを取得"""
        try:
            if not os.path.exists(self.platform_directory):
                self.platform_directory = self.find_account_directory()
                
            if not os.path.exists(self.platform_directory):
                return {}
            
            files_info = {}
            for filename in os.listdir(self.platform_directory):
                if filename.endswith('.mp4'):
                    filepath = os.path.join(self.platform_directory, filename)
                    try:
                        size = os.path.getsize(filepath)
                        files_info[filename] = size
                    except OSError:
                        continue
            
            return files_info
        except Exception as e:
            self.error_callback(self.user_name, f"ディレクトリアクセスエラー: {str(e)}")
            return {}

    def extract_lv_value(self, filename):
        match = re.search(r'lv\d+', filename)
        if match:
            return match.group()
        return None

    def call_pipeline(self, lv_value):
        try:
            print(f"DEBUG: [{self.user_name}] パイプライン呼び出し開始: {lv_value}")
            
            import sys
            python_executable = sys.executable
            
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            cmd = [
                python_executable,
                'pipeline.py',
                self.config["basic_settings"]["platform"],
                self.config["basic_settings"]["account_id"],
                self.config["basic_settings"]["platform_directory"],
                self.config["basic_settings"]["ncv_directory"],
                lv_value,
            ]
            
            print(f"DEBUG: [{self.user_name}] 実行コマンド: {' '.join(cmd)}")
            
            # Popenでリアルタイム出力
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # リアルタイムで行ごとに出力
            for line in iter(process.stdout.readline, ''):
                print(line.rstrip())
            
            process.wait()
            print(f"DEBUG: [{self.user_name}] パイプライン終了コード: {process.returncode}")
            
            if process.returncode == 0:
                self.logger.log(f"[{self.user_name}] パイプライン処理完了: {lv_value}")
                
        except Exception as e:
            print(f"DEBUG: [{self.user_name}] パイプライン呼び出しエラー: {str(e)}")

    def start_watching(self):
        if not self.running:
            self.running = True
            
            # watchdogでファイルシステム監視開始
            self.observer = Observer()
            event_handler = Mp4FileHandler(self)
            self.observer.schedule(event_handler, self.platform_directory, recursive=False)
            self.observer.start()
            
            print(f"DEBUG: [{self.user_name}] watchdog監視開始: {self.platform_directory}")
            self.logger.log(f"[{self.user_name}] 監視開始: {self.platform_directory}")

    def stop_watching(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print(f"DEBUG: [{self.user_name}] watchdog監視停止")
        
        # 実行中のタイマーをすべてキャンセル
        for timer in self.stability_threads.values():
            timer.cancel()
        self.stability_threads.clear()

# MultiUserMonitorクラスは変更なし
class MultiUserMonitor:
    def __init__(self, logger, error_callback):
        self.logger = logger
        self.error_callback = error_callback
        self.active_watchers = {}
    
    def start_user_watch(self, user_name, config):
        if user_name not in self.active_watchers:
            monitor = Mp4Monitor(user_name, config, self.logger, self.error_callback)
            self.active_watchers[user_name] = monitor
            monitor.start_watching()
            return True
        return False
    
    def stop_user_watch(self, user_name):
        if user_name in self.active_watchers:
            monitor = self.active_watchers[user_name]
            monitor.stop_watching()
            del self.active_watchers[user_name]
            self.logger.log(f"[{user_name}] 監視停止")
            return True
        return False
    
    def is_watching(self, user_name):
        return user_name in self.active_watchers
    
    def stop_all(self):
        for user_name in list(self.active_watchers.keys()):
            self.stop_user_watch(user_name)