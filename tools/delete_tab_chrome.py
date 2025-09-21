import subprocess
import time
import psutil
import logging
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, NoSuchWindowException

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tab_delete_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

DEBUGLOG = logging.getLogger(__name__)

# Chrome設定
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeDebug"
PROFILE_NAME = "Default"
DEBUG_PORT = "9222"

# テスト用タブID
TEST_TAB_ID = "8B083E3060DF6D1BFEE99DAB7A256158"

def is_debug_chrome_running():
    """デバッグモードのChromeが起動中かチェック"""
    DEBUGLOG.debug("デバッグChrome存在チェック開始")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
            cmdline = " ".join(proc.info['cmdline']).lower()
            if USER_DATA_DIR.lower() in cmdline and f"--remote-debugging-port={DEBUG_PORT}" in cmdline:
                DEBUGLOG.info(f"デバッグChrome発見! PID: {proc.info['pid']}")
                return True
    
    DEBUGLOG.info("デバッグChrome存在: False")
    return False

def connect_selenium():
    """SeleniumでデバッグモードのChromeに接続"""
    DEBUGLOG.debug("Selenium接続開始")
    
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        
        driver = webdriver.Chrome(options=chrome_options)
        DEBUGLOG.info("Selenium接続成功")
        return driver
    except WebDriverException as e:
        DEBUGLOG.error(f"Selenium接続失敗: {e}")
        return None

def list_all_tabs(driver):
    """現在開いているすべてのタブを列挙"""
    DEBUGLOG.info("現在のタブ一覧を取得中...")
    
    try:
        all_handles = driver.window_handles
        DEBUGLOG.info(f"総タブ数: {len(all_handles)}")
        
        for i, handle in enumerate(all_handles):
            try:
                # 各タブに一時切り替えしてタイトルとURLを取得
                original_handle = driver.current_window_handle
                driver.switch_to.window(handle)
                
                title = driver.title
                url = driver.current_url
                
                DEBUGLOG.info(f"タブ{i+1}: {handle}")
                DEBUGLOG.info(f"  タイトル: {title}")
                DEBUGLOG.info(f"  URL: {url}")
                
                # 元のタブに戻る
                if original_handle in all_handles:
                    driver.switch_to.window(original_handle)
                
            except Exception as e:
                DEBUGLOG.warning(f"タブ{i+1}({handle})の情報取得失敗: {e}")
        
        return all_handles
        
    except Exception as e:
        DEBUGLOG.error(f"タブ一覧取得エラー: {e}")
        return []

def check_tab_exists(driver, tab_id):
    """指定されたタブIDが存在するかチェック"""
    DEBUGLOG.info(f"タブ存在確認: {tab_id}")
    
    try:
        all_handles = driver.window_handles
        DEBUGLOG.debug(f"現在のタブハンドル一覧: {all_handles}")
        
        if tab_id in all_handles:
            DEBUGLOG.info(f"タブが存在します: {tab_id}")
            return True
        else:
            DEBUGLOG.warning(f"タブが見つかりません: {tab_id}")
            return False
            
    except Exception as e:
        DEBUGLOG.error(f"タブ存在確認エラー: {e}")
        return False

def close_tab_by_id(driver, tab_id):
    """指定されたタブIDのタブを閉じる"""
    DEBUGLOG.info(f"タブ削除開始: {tab_id}")
    
    try:
        # タブの存在確認
        if not check_tab_exists(driver, tab_id):
            DEBUGLOG.error("削除対象タブが見つかりません")
            return False
        
        # 現在のタブを記録
        original_handle = driver.current_window_handle
        DEBUGLOG.debug(f"削除前の現在タブ: {original_handle}")
        
        # 削除対象タブに切り替え
        DEBUGLOG.info("削除対象タブに切り替え中...")
        driver.switch_to.window(tab_id)
        
        # 切り替え確認
        current_handle = driver.current_window_handle
        if current_handle != tab_id:
            DEBUGLOG.error(f"タブ切り替え失敗 - 期待:{tab_id}, 実際:{current_handle}")
            return False
        
        DEBUGLOG.info("タブ切り替え成功")
        
        # タブのタイトルとURLを記録（削除前の最終確認）
        try:
            title = driver.title
            url = driver.current_url
            DEBUGLOG.info(f"削除対象タブ情報:")
            DEBUGLOG.info(f"  タイトル: {title}")
            DEBUGLOG.info(f"  URL: {url}")
        except:
            DEBUGLOG.warning("削除対象タブの詳細情報取得に失敗")
        
        # タブを閉じる
        DEBUGLOG.info("タブ削除実行...")
        driver.close()
        
        # 削除後の確認
        time.sleep(1)
        remaining_handles = driver.window_handles
        
        if tab_id not in remaining_handles:
            DEBUGLOG.info(f"タブ削除成功: {tab_id}")
            DEBUGLOG.info(f"残りタブ数: {len(remaining_handles)}")
            
            # 他にタブがある場合は適当なタブに切り替え
            if remaining_handles:
                switch_target = remaining_handles[0]
                DEBUGLOG.info(f"別タブに切り替え: {switch_target}")
                driver.switch_to.window(switch_target)
            else:
                DEBUGLOG.info("すべてのタブが削除されました")
            
            return True
        else:
            DEBUGLOG.error("タブ削除に失敗（まだ存在しています）")
            return False
            
    except NoSuchWindowException:
        DEBUGLOG.info("タブは既に閉じられています")
        return True
    except Exception as e:
        DEBUGLOG.error(f"タブ削除処理でエラー: {e}", exc_info=True)
        return False

def main():
    """メイン処理"""
    print("タブ削除テストスクリプト")
    print("=" * 50)
    print(f"削除対象タブID: {TEST_TAB_ID}")
    print()
    
    DEBUGLOG.info("タブ削除テスト開始")
    
    try:
        # 1. デバッグChromeの確認
        if not is_debug_chrome_running():
            DEBUGLOG.error("デバッグモードのChromeが起動していません")
            print("エラー: デバッグChromeが見つかりません")
            return False
        
        # 2. Selenium接続
        driver = connect_selenium()
        if not driver:
            DEBUGLOG.error("Chrome接続に失敗しました")
            print("エラー: Chrome接続失敗")
            return False
        
        # 3. 削除前の状態確認
        print("削除前のタブ一覧:")
        list_all_tabs(driver)
        
        # 4. タブ削除実行
        print(f"\nタブ削除実行: {TEST_TAB_ID}")
        success = close_tab_by_id(driver, TEST_TAB_ID)
        
        if success:
            print("✅ タブ削除成功")
        else:
            print("❌ タブ削除失敗")
        
        # 5. 削除後の状態確認
        print("\n削除後のタブ一覧:")
        list_all_tabs(driver)
        
        return success
        
    except Exception as e:
        DEBUGLOG.error(f"メイン処理でエラー: {e}", exc_info=True)
        print(f"エラー: {e}")
        return False
    
    finally:
        # Seleniumドライバを閉じない（デバッグChromeは残す）
        DEBUGLOG.info("テスト完了")

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 タブ削除テスト完了")
    else:
        print("\n💥 タブ削除テスト失敗")