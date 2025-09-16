import os
import re
import time
import subprocess
import threading
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

        self.display_name = config.get("display_name", "")

        platform_dir = config["basic_settings"]["platform_directory"]
        self.base_platform_directory = platform_dir if os.path.isabs(platform_dir) else os.path.abspath(platform_dir)

        self.platform_directory = self.find_account_directory()

        # 内部状態
        self.running = False
        self.observer = None
        self.poll_interval = 5  # 秒
        self.running_lvs = set()       # 実行中lvのロック
        self.ignored_files = set()     # 既存ファイルなど
        self.stability_workers = {}    # {filename: Thread}

        self.initialize_ignored_files()

    # ---------- 初期化 ----------
    def initialize_ignored_files(self):
        try:
            if os.path.exists(self.platform_directory):
                existing = self.get_mp4_files_with_size()
                self.ignored_files = set(existing.keys())
                if self.ignored_files:
                    print(f"DEBUG: [{self.user_name}] 既存ファイルを無視リストに追加: {list(self.ignored_files)}")
                else:
                    print(f"DEBUG: [{self.user_name}] 既存ファイルなし")
            else:
                print(f"DEBUG: [{self.user_name}] 監視ディレクトリが存在しないため、無視リストは空")
        except Exception as e:
            print(f"DEBUG: [{self.user_name}] 無視リスト初期化エラー: {str(e)}")
            self.ignored_files = set()

    def find_account_directory(self):
        try:
            account_id = str(self.config["basic_settings"]["account_id"])
            base = self.base_platform_directory

            if not os.path.exists(base):
                self.logger.log(f"[{self.user_name}] 監視ディレクトリが存在しません: {base}")
                return base

            for dirname in os.listdir(base):
                dir_path = os.path.join(base, dirname)
                if os.path.isdir(dir_path) and dirname.startswith(account_id):
                    self.logger.log(f"[{self.user_name}] アカウントディレクトリ発見: {dir_path}")
                    return dir_path

            # 見つからなければ作成
            account_dir = os.path.join(base, f"{account_id}_{self.display_name or 'user'}")
            os.makedirs(account_dir, exist_ok=True)
            self.logger.log(f"[{self.user_name}] アカウントディレクトリ作成: {account_dir}")
            return account_dir

        except Exception as e:
            self.error_callback(self.user_name, f"アカウントディレクトリ検索エラー: {str(e)}")
            return self.base_platform_directory

    def get_mp4_files_with_size(self):
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
                        files_info[filename] = os.path.getsize(filepath)
                    except OSError:
                        pass
            return files_info
        except Exception as e:
            self.error_callback(self.user_name, f"ディレクトリアクセスエラー: {str(e)}")
            return {}

    @staticmethod
    def extract_lv_value(filename):
        m = re.search(r'lv\d+', filename)
        return m.group() if m else None

    # ---------- 監視イベント ----------
    def handle_new_file(self, filename):
        if filename in self.ignored_files:
            return
        self._start_stability_worker(filename)

    def handle_file_change(self, filename):
        if filename in self.ignored_files:
            return
        self._start_stability_worker(filename)
        print(f"DEBUG: [{self.user_name}] ファイル変更検出、安定性チェック再開: {filename}")

    # ---------- 安定判定ワーカー ----------
    def _start_stability_worker(self, filename):
        # すでにそのファイルのワーカーが走っていれば何もしない
        if filename in self.stability_workers and self.stability_workers[filename].is_alive():
            return

        th = threading.Thread(target=self._stability_worker, args=(filename,), daemon=True)
        self.stability_workers[filename] = th
        th.start()

    def _stability_worker(self, filename):
        """サイズをポーリングし、連続2回同サイズになったら安定とみなす"""
        path = os.path.join(self.platform_directory, filename)
        last_size = None
        same_count = 0

        while True:
            if not os.path.exists(path):
                print(f"DEBUG: [{self.user_name}] ファイル消失: {filename}")
                return

            try:
                current_size = os.path.getsize(path)
            except OSError:
                current_size = None

            if last_size is not None and current_size == last_size:
                same_count += 1
                # 2回連続で同一サイズ → 安定
                if same_count >= 1:
                    print(f"DEBUG: [{self.user_name}] サイズ変化なし → 安定: {filename}")
                    self._on_file_stable(filename)
                    return
            else:
                if last_size is None:
                    print(f"DEBUG: [{self.user_name}] 初回サイズ記録: {filename} -> {current_size} bytes（次回チェックへ）")
                else:
                    print(f"DEBUG: [{self.user_name}] サイズ変化中 {filename}: {last_size} -> {current_size} bytes（再チェック）")
                same_count = 0
                last_size = current_size

            time.sleep(self.poll_interval)

    def _on_file_stable(self, filename):
        lv_value = self.extract_lv_value(filename)
        if not lv_value:
            print(f"DEBUG: [{self.user_name}] lv値が見つかりません: {filename}")
            return

        if lv_value in self.running_lvs:
            print(f"DEBUG: [{self.user_name}] すでに起動中のためスキップ: {lv_value}")
            return

        self.running_lvs.add(lv_value)
        try:
            print(f"DEBUG: [{self.user_name}] lv値抽出成功: {lv_value}")
            self.call_pipeline(lv_value)
            # 完了したファイルは以後無視
            self.ignored_files.add(filename)
        finally:
            self.running_lvs.discard(lv_value)

    # ---------- パイプライン ----------
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

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )

            for line in iter(proc.stdout.readline, ''):
                print(line.rstrip())

            proc.wait()
            print(f"DEBUG: [{self.user_name}] パイプライン終了コード: {proc.returncode}")

            if proc.returncode == 0:
                self.logger.log(f"[{self.user_name}] パイプライン処理完了: {lv_value}")
            else:
                self.logger.log(f"[{self.user_name}] パイプライン処理失敗({proc.returncode}): {lv_value}")

        except Exception as e:
            print(f"DEBUG: [{self.user_name}] パイプライン呼び出しエラー: {str(e)}")

    # ---------- 監視の開始/停止 ----------
    def start_watching(self):
        if self.running:
            return
        self.running = True

        if not os.path.exists(self.platform_directory):
            print(f"DEBUG: [{self.user_name}] 監視ディレクトリが存在しないため作成: {self.platform_directory}")
            try:
                os.makedirs(self.platform_directory, exist_ok=True)
            except Exception as e:
                print(f"DEBUG: [{self.user_name}] ディレクトリ作成エラー: {str(e)}")
                self.logger.log(f"[{self.user_name}] 監視開始失敗: ディレクトリ作成エラー")
                self.running = False
                return

        self.observer = Observer()
        self.observer.schedule(Mp4FileHandler(self), self.platform_directory, recursive=False)

        try:
            self.observer.start()
            print(f"DEBUG: [{self.user_name}] watchdog監視開始: {self.platform_directory}")
            self.logger.log(f"[{self.user_name}] 監視開始: {self.platform_directory}")
        except Exception as e:
            print(f"DEBUG: [{self.user_name}] watchdog開始エラー: {str(e)}")
            self.logger.log(f"[{self.user_name}] 監視開始失敗: {str(e)}")
            self.running = False

    def stop_watching(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print(f"DEBUG: [{self.user_name}] watchdog監視停止")

        # ワーカーはデーモンなのでプロセス終了で止まる
        self.stability_workers.clear()


class MultiUserMonitor:
    def __init__(self, logger, error_callback):
        self.logger = logger
        self.error_callback = error_callback
        self.active_watchers = {}

    def start_user_watch(self, user_name, config):
        if user_name in self.active_watchers:
            return False
        monitor = Mp4Monitor(user_name, config, self.logger, self.error_callback)
        self.active_watchers[user_name] = monitor
        monitor.start_watching()
        return True

    def stop_user_watch(self, user_name):
        if user_name not in self.active_watchers:
            return False
        monitor = self.active_watchers.pop(user_name)
        monitor.stop_watching()
        self.logger.log(f"[{user_name}] 監視停止")
        return True

    def is_watching(self, user_name):
        return user_name in self.active_watchers

    def stop_all(self):
        for user_name in list(self.active_watchers.keys()):
            self.stop_user_watch(user_name)
