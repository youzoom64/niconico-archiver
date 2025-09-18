import subprocess
import time
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

class ChromeRecorderController:
    def __init__(self, target_url):
        self.target_url = target_url
        self.debug_port = 9222
        self.chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.user_data_dir = r"C:\ChromeDebug"
        self.profile_name = "Profile 3"
        self.driver = None

    def is_chrome_debug_running(self):
        for proc in psutil.process_iter(['name', 'cmdline']):
            if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']).lower()
                if self.user_data_dir.lower() in cmdline and f"--remote-debugging-port={self.debug_port}" in cmdline:
                    return True
        return False

    def start_chrome_debug(self):
        if self.is_chrome_debug_running():
            print("Debug Chrome is already running")
            return True

        print("Starting Chrome in debug mode...")
        subprocess.Popen([
            self.chrome_path,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={self.user_data_dir}",
            f"--profile-directory={self.profile_name}",
            "--disable-extensions-except=" + r"C:\project_root\app_workspaces\multi-tab-recorder",
            "--load-extension=" + r"C:\project_root\app_workspaces\multi-tab-recorder"
        ])
        
        for i in range(10):
            time.sleep(1)
            if self.is_chrome_debug_running():
                print("Chrome debug mode started successfully")
                return True
        print("Failed to start Chrome debug mode")
        return False

    def connect_selenium(self):
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("Connected to Chrome via Selenium")
            return True
        except WebDriverException as e:
            print(f"Failed to connect to Chrome: {e}")
            return False

    def navigate_to_url(self):
        try:
            print(f"Navigating to: {self.target_url}")
            self.driver.get(self.target_url)
            time.sleep(3)
            print("Page loaded successfully")
            return True
        except Exception as e:
            print(f"Failed to navigate to URL: {e}")
            return False

    def wait_for_manual_recording(self, wait_duration=30):
        """録画開始を手動で行うための待機"""
        print("=" * 50)
        print("🎥 MANUAL RECORDING REQUIRED")
        print("=" * 50)
        print("Please manually:")
        print("1. Click the extension icon in Chrome toolbar")
        print("2. Click the 'Start' button to begin recording")
        print("3. Wait for recording to complete")
        print("4. Click 'Stop' when finished")
        print("=" * 50)
        print(f"Waiting {wait_duration} seconds for manual operation...")
        
        for remaining in range(wait_duration, 0, -1):
            if remaining % 5 == 0:
                print(f"Time remaining: {remaining} seconds")
            time.sleep(1)
        
        print("Manual recording time completed")
        return True

    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.driver:
            try:
                self.driver.quit()
                print("Selenium driver closed")
            except Exception as e:
                print(f"Error closing driver: {e}")

    def run_recording_session(self, manual_wait_duration=30):
        """録画セッション全体を実行（手動録画）"""
        try:
            # 1. Chrome起動
            if not self.start_chrome_debug():
                return False
            
            # 2. Selenium接続
            if not self.connect_selenium():
                return False
            
            # 3. 対象URLにアクセス
            if not self.navigate_to_url():
                return False
            
            # 4. 手動録画の待機
            if not self.wait_for_manual_recording(manual_wait_duration):
                return False
            
            print("Recording session completed")
            return True
            
        except Exception as e:
            print(f"Error in recording session: {e}")
            return False
        finally:
            # self.cleanup()  # Chromeは起動したまま
            pass

def main():
    TARGET_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    MANUAL_WAIT_DURATION = 60  # 手動操作用の待機時間（秒）
    
    controller = ChromeRecorderController(TARGET_URL)
    success = controller.run_recording_session(MANUAL_WAIT_DURATION)
    
    if success:
        print("Session completed - recording should be saved")
    else:
        print("Session failed")

if __name__ == "__main__":
    main()