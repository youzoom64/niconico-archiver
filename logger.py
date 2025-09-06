import os
import logging
from datetime import datetime

class Logger:
    def __init__(self):
        # 絶対パスに変換
        self.log_dir = os.path.abspath("logs")
        self.log_file = os.path.join(self.log_dir, "watchdog.log")
        self.setup_logger()
        
    def setup_logger(self):
        """ログ設定を初期化"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # ログフォーマットを設定
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイルハンドラを設定
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # ロガーを設定
        self.logger = logging.getLogger('watchdog')
        self.logger.setLevel(logging.INFO)
        
        # 既存のハンドラをクリア
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
    
    def log(self, message, level='INFO'):
        """ログメッセージを記録"""
        if level == 'INFO':
            self.logger.info(message)
        elif level == 'ERROR':
            self.logger.error(message)
        elif level == 'WARNING':
            self.logger.warning(message)
        elif level == 'DEBUG':
            self.logger.debug(message)
    
    def info(self, message):
        """INFOレベルでログ記録"""
        self.log(message, 'INFO')
    
    def error(self, message):
        """ERRORレベルでログ記録"""
        self.log(message, 'ERROR')
    
    def warning(self, message):
        """WARNINGレベルでログ記録"""
        self.log(message, 'WARNING')
    
    def debug(self, message):
        """DEBUGレベルでログ記録"""
        self.log(message, 'DEBUG')
    
    def get_recent_logs(self, lines=50):
        """最近のログを取得"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        return ""
    
    def clear_logs(self):
        """ログファイルをクリア"""
        if os.path.exists(self.log_file):
            open(self.log_file, 'w').close()