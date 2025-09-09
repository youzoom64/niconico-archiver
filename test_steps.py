import sys
import os
import json
import importlib
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append('.')

def load_test_config():
    """テスト用の設定を読み込み"""
    test_config = {
        "account_id": "test123",
        "display_name": "テストアカウント",
        "basic_settings": {
            "platform": "niconico",
            "account_id": "test123",
            "platform_directory": "test_rec",
            "ncv_directory": "test_ncv"
        },
        "api_settings": {
            "ai_model": "openai-gpt4o",
            "openai_api_key": "",  # 必要に応じて設定
            "google_api_key": "",
            "suno_api_key": "",
            "imgur_api_key": ""
        },
        "ai_features": {
            "enable_summary_text": True,
            "enable_summary_image": True,
            "enable_ai_music": True,
            "enable_ai_conversation": True
        },
        "ai_prompts": {
            "summary_prompt": "以下の配信内容を日本語で要約してください:",
            "image_prompt": "この配信の抽象的なイメージを生成してください:"
        },
        "display_features": {
            "enable_emotion_scores": True,
            "enable_comment_ranking": True,
            "enable_word_ranking": True,
            "enable_thumbnails": True
        },
        "special_users": ["116071760", "67890"]
    }
    return test_config

def create_test_pipeline_data(lv_value="lv999999999"):
    """テスト用のパイプラインデータを作成"""
    config = load_test_config()
    return {
        'platform': config['basic_settings']['platform'],
        'account_id': config['basic_settings']['account_id'],
        'platform_directory': config['basic_settings']['platform_directory'],
        'ncv_directory': config['basic_settings']['ncv_directory'],
        'lv_value': lv_value,
        'user_name': config['account_id'],
        'config': config,
        'start_time': datetime.now(),
        'results': {}
    }

def get_available_steps():
    """利用可能なステップ一覧を取得"""
    steps = [
        'step01_data_collector',
        'step02_audio_transcriber',
        'step03_emotion_scorer', 
        'step04_word_analyzer',
        'step05_summarizer',
        'step06_special_user_html_generator',
        'step07_music_generator',
        'step08_image_generator'
    ]
    return steps

def test_single_step(step_name, pipeline_data):
    """単一ステップをテスト実行"""
    try:
        print(f"\n{'='*50}")
        print(f"🚀 テスト実行: {step_name}")
        print(f"{'='*50}")
        
        # モジュールを動的読み込み
        module = importlib.import_module(f"processors.{step_name}")
        
        # process関数を実行
        if hasattr(module, 'process'):
            result = module.process(pipeline_data)
            print(f"✅ {step_name} 完了!")
            print(f"📊 結果: {result}")
            return result
        else:
            print(f"❌ {step_name} には process関数がありません")
            return None
            
    except ImportError as e:
        print(f"❌ {step_name} モジュールが見つかりません: {e}")
        return None
    except Exception as e:
        print(f"❌ {step_name} でエラー発生: {e}")
        return None

def interactive_menu():
    """対話式メニュー"""
    steps = get_available_steps()
    
    while True:
        print(f"\n{'='*60}")
        print("🎯 ステップテストツール")
        print(f"{'='*60}")
        
        print("📋 利用可能なステップ:")
        for i, step in enumerate(steps, 1):
            print(f"  {i:2d}. {step}")
        
        print(f"\n⚡ 特別オプション:")
        print(f"  {len(steps)+1:2d}. 全ステップ実行")
        print(f"  {len(steps)+2:2d}. カスタムlv値で実行")
        print(f"  {len(steps)+3:2d}. 設定確認")
        print(f"   0. 終了")
        
        try:
            choice = int(input(f"\n🎮 選択してください (0-{len(steps)+3}): "))
            
            if choice == 0:
                print("👋 テストツールを終了します")
                break
            elif 1 <= choice <= len(steps):
                # 単一ステップ実行
                step_name = steps[choice-1]
                lv_value = input("📺 lv値を入力 (Enter=デフォルト): ").strip()
                if not lv_value:
                    lv_value = "lv999999999"
                
                pipeline_data = create_test_pipeline_data(lv_value)
                test_single_step(step_name, pipeline_data)
                
            elif choice == len(steps)+1:
                # 全ステップ実行
                lv_value = input("📺 lv値を入力 (Enter=デフォルト): ").strip()
                if not lv_value:
                    lv_value = "lv999999999"
                    
                pipeline_data = create_test_pipeline_data(lv_value)
                print(f"\n🚀 全ステップを順次実行開始...")
                
                for step_name in steps:
                    result = test_single_step(step_name, pipeline_data)
                    if result:
                        pipeline_data['results'][step_name] = result
                    
                    input("⏸️  次のステップに進むには Enter を押してください...")
                
                print("🎉 全ステップ実行完了!")
                
            elif choice == len(steps)+2:
                # カスタムlv値
                lv_value = input("📺 カスタムlv値を入力: ").strip()
                if lv_value:
                    print("📋 実行するステップを選択:")
                    for i, step in enumerate(steps, 1):
                        print(f"  {i:2d}. {step}")
                    
                    step_choice = int(input("ステップ番号: "))
                    if 1 <= step_choice <= len(steps):
                        pipeline_data = create_test_pipeline_data(lv_value)
                        test_single_step(steps[step_choice-1], pipeline_data)
                
            elif choice == len(steps)+3:
                # 設定確認
                config = load_test_config()
                print(f"\n📋 現在のテスト設定:")
                print(json.dumps(config, ensure_ascii=False, indent=2))
                
            else:
                print("❌ 無効な選択です")
                
        except ValueError:
            print("❌ 数値を入力してください")
        except KeyboardInterrupt:
            print("\n👋 テストツールを終了します")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")

def quick_test(step_name, lv_value="lv999999999"):
    """クイックテスト用関数"""
    pipeline_data = create_test_pipeline_data(lv_value)
    return test_single_step(step_name, pipeline_data)

if __name__ == "__main__":
    print("🎯 ニコ生アーカイブ処理ステップテストツール")
    print("各処理ステップを個別にテスト実行できます")
    
    # コマンドライン引数でクイック実行
    if len(sys.argv) > 1:
        step_name = sys.argv[1]
        lv_value = sys.argv[2] if len(sys.argv) > 2 else "lv999999999"
        quick_test(step_name, lv_value)
    else:
        interactive_menu()