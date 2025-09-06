import os
import time
import re
import subprocess
import threading
from datetime import datetime

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
        self.thread = None
        self.file_sizes = {}  # ファイルサイズ記録用
        
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
            # ディレクトリが見つからない場合は再検索
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
    
    def is_file_stable(self, filename, current_size):
        """ファイルサイズが5秒間変化していないかチェック"""
        current_time = time.time()
        
        if filename not in self.file_sizes:
            # 初回検出
            self.file_sizes[filename] = {
                'size': current_size,
                'last_change': current_time,
                'stable': False
            }
            return False
        
        file_info = self.file_sizes[filename]
        
        if file_info['size'] != current_size:
            # サイズが変化した
            file_info['size'] = current_size
            file_info['last_change'] = current_time
            file_info['stable'] = False
            return False
        
        # サイズが変化していない場合、5秒経過したかチェック
        if current_time - file_info['last_change'] >= 5.0:
            if not file_info['stable']:
                file_info['stable'] = True
                return True
        
        return False
    
    def extract_lv_value(self, filename):
        match = re.search(r'lv\d+', filename)
        if match:
            return match.group()
        return None
    
    def call_pipeline(self, lv_value):
        try:
            cmd = [
                'python', 'pipeline.py',
                self.config["basic_settings"]["platform"],
                self.config["basic_settings"]["account_id"],
                self.config["basic_settings"]["platform_directory"],
                self.config["basic_settings"]["ncv_directory"],
                lv_value,
                self.user_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode != 0:
                self.error_callback(self.user_name, f"パイプライン処理失敗: {result.stderr}")
            else:
                self.logger.log(f"[{self.user_name}] パイプライン処理完了: {lv_value}")
                
        except subprocess.TimeoutExpired:
            self.error_callback(self.user_name, "パイプライン処理がタイムアウトしました")
        except Exception as e:
            self.error_callback(self.user_name, f"パイプライン呼び出しエラー: {str(e)}")
    
    def watch_loop(self):
        self.logger.log(f"[{self.user_name}] 監視開始: {self.platform_directory}")
        
        while self.running:
            try:
                current_files = self.get_mp4_files_with_size()
                
                # 各ファイルのサイズ変化をチェック
                for filename, current_size in current_files.items():
                    if self.is_file_stable(filename, current_size):
                        self.logger.log(f"[{self.user_name}] ファイルが安定: {filename} (サイズ: {current_size})")
                        
                        lv_value = self.extract_lv_value(filename)
                        if lv_value:
                            self.logger.log(f"[{self.user_name}] lv値抽出: {lv_value}")
                            self.call_pipeline(lv_value)
                        else:
                            self.logger.log(f"[{self.user_name}] lv値が見つかりません: {filename}")
                
                # 削除されたファイルの記録をクリーンアップ
                existing_files = set(current_files.keys())
                recorded_files = set(self.file_sizes.keys())
                deleted_files = recorded_files - existing_files
                
                for deleted_file in deleted_files:
                    del self.file_sizes[deleted_file]
                    self.logger.log(f"[{self.user_name}] ファイル削除を検出: {deleted_file}")
                
                time.sleep(1)  # 1秒間隔でチェック
                
            except Exception as e:
                self.error_callback(self.user_name, f"監視ループエラー: {str(e)}")
                break
    
    def start_watching(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.watch_loop, daemon=True)
            self.thread.start()
    
    def stop_watching(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


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