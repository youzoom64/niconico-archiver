import sys
import os
sys.path.append('.')

from processors.step11_06_special_user_html_generator import process
from config_manager import ConfigManager

# テスト用のpipeline_dataを作成
def test_step11_06():
    account_id = "123"  # あなたのアカウントID
    lv_value = "lv123456"  # テスト対象のlv値
    
    config_manager = ConfigManager()
    config = config_manager.load_user_config(account_id)
    
    pipeline_data = {
        'platform': 'niconico',
        'account_id': account_id,
        'platform_directory': config['basic_settings']['platform_directory'],
        'ncv_directory': config['basic_settings']['ncv_directory'],
        'lv_value': lv_value,
        'user_name': account_id,
        'config': config,
        'results': {}
    }
    
    # step11_06を実行
    try:
        result = process(pipeline_data)
        print(f"実行結果: {result}")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_step11_06()