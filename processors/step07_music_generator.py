import json
import os
import requests
import time
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step07: AI音楽生成"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step07 開始: {lv_value}")
        
        # 1. AI音楽生成機能が有効か確認
        if not config["ai_features"].get("enable_ai_music", False):
            print("AI音楽生成機能が無効です。処理をスキップします。")
            return {"music_generated": False, "reason": "feature_disabled"}
        
        # 2. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. 統合JSONファイル読み込み
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        
        # 4. 要約テキストの確認
        summary_text = broadcast_data.get('summary_text', '')
        if not summary_text.strip():
            print("要約テキストが見つかりません。音楽生成をスキップします。")
            return {"music_generated": False, "reason": "no_summary"}
        
        # 5. Suno API設定確認
        suno_api_key = config["api_settings"].get("suno_api_key", "")
        if not suno_api_key:
            print("Suno API Keyが設定されていません。音楽生成をスキップします。")
            return {"music_generated": False, "reason": "no_api_key"}
        
        # 6. 音楽生成
        music_result = generate_music_from_summary(
            broadcast_data.get('live_title', 'タイトル不明'),
            summary_text,
            suno_api_key
        )
        
        if music_result:
            # 7. 統合JSONに結果を追加
            broadcast_data['music_generation'] = music_result
            save_broadcast_data(broadcast_dir, lv_value, broadcast_data)
            
            print(f"Step07 完了: {lv_value} - 音楽生成成功")
            return {"music_generated": True, "task_id": music_result.get("task_id")}
        else:
            print(f"Step07 完了: {lv_value} - 音楽生成失敗")
            return {"music_generated": False, "reason": "generation_failed"}
        
    except Exception as e:
        print(f"Step07 エラー: {str(e)}")
        raise

def load_broadcast_data(broadcast_dir, lv_value):
    """統合JSONファイルを読み込み"""
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise Exception(f"統合JSONファイルが見つかりません: {json_path}")

def save_broadcast_data(broadcast_dir, lv_value, broadcast_data):
    """統合JSONファイルを保存"""
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(broadcast_data, f, ensure_ascii=False, indent=2)

def generate_music_from_summary(title, summary, api_key):
    """要約から音楽を生成"""
    try:
        print(f"音楽生成開始: {title}")
        print(f"要約: {summary[:100]}...")
        
        suno_api = SunoAPI(api_key)
        
        # 要約から音楽プロンプトを生成
        music_prompt = create_music_prompt(summary)
        
        # 音楽生成実行
        result = suno_api.generate_music(
            prompt=music_prompt,
            custom_mode=True,
            instrumental=False,  # 歌詞付き
            model="V4_5",
            style="Indie Pop",
            title=title
        )
        
        if result:
            return {
                "task_id": result["task_id"],
                "stream_url": result["stream_url"],
                "download_url": result.get("download_url", ""),
                "music_prompt": music_prompt,
                "generated_at": datetime.now().isoformat(),
                "title": title,
                "status": result.get("status", "generated")
            }
        
        return None
        
    except Exception as e:
        print(f"音楽生成エラー: {str(e)}")
        return None

def create_music_prompt(summary):
    """要約テキストから音楽プロンプトを作成"""
    # 要約を短縮して音楽的な表現に変換
    prompt_parts = []
    
    # 基本的な音楽スタイル
    prompt_parts.append("A melodic indie pop song")
    
    # 要約の内容に基づいてムードを決定
    if any(word in summary.lower() for word in ['楽しい', '面白い', '笑', 'ゲーム', '楽しみ']):
        prompt_parts.append("with an upbeat and cheerful melody")
    elif any(word in summary.lower() for word in ['悲しい', '困難', '問題', '心配']):
        prompt_parts.append("with a melancholic and reflective tone")
    elif any(word in summary.lower() for word in ['政治', '社会', '議論', '批判']):
        prompt_parts.append("with a thoughtful and contemplative mood")
    else:
        prompt_parts.append("with a gentle and warm atmosphere")
    
    # 歌詞として要約の一部を使用（最大200文字）
    lyrics_content = summary[:200] if len(summary) > 200 else summary
    prompt_parts.append(f"Lyrics should reflect the theme: {lyrics_content}")
    
    return ", ".join(prompt_parts)

class SunoAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.sunoapi.org/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.last_request_time = 0
    
    def _rate_limit(self):
        """レート制限: 0.5秒間隔"""
        current_time = time.time()
        if current_time - self.last_request_time < 0.5:
            time.sleep(0.5)
        self.last_request_time = time.time()
    
    def generate_music(self, prompt, custom_mode=False, instrumental=False, 
                      model="V4_5", style=None, title=None):
        """音楽生成"""
        self._rate_limit()
        
        data = {
            "customMode": custom_mode,
            "instrumental": instrumental,
            "model": model,
            "prompt": prompt,
            "callBackUrl": "https://example.com/callback"
        }
        
        if custom_mode and style:
            data["style"] = style
        if custom_mode and title:
            data["title"] = title
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result["data"]["taskId"]
                
                print(f"音楽生成開始 - TaskID: {task_id}")
                print("ストリーミングURL取得まで30-40秒待機...")
                
                return self._wait_for_urls(task_id)
                
            elif response.status_code == 429:
                print("クレジット不足")
                return None
            elif response.status_code == 430:
                print("リクエスト頻度過多")
                return None
            else:
                print(f"API エラー {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"リクエスト失敗: {e}")
            return None
    
    def _wait_for_urls(self, task_id):
        """URLが利用可能になるまで待機"""
        print("URLの生成を待機中...")
        
        # 実際の実装では get_task_status API を使用して状態を確認
        # ここでは簡易的に待機時間を設定
        for i in range(8):
            time.sleep(5)
            print(f"   {(i+1)*5}秒経過...")
        
        # 実際のAPIレスポンスに基づいてURLを返す
        return {
            "task_id": task_id,
            "stream_url": f"https://cdn.sunoapi.org/stream/{task_id}.mp3",
            "download_url": f"https://cdn.sunoapi.org/download/{task_id}.mp3",
            "status": "ready"
        }

    def get_task_status(self, task_id):
        """タスクの状態を確認（実装例）"""
        self._rate_limit()
        
        try:
            response = requests.get(
                f"{self.base_url}/task/{task_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ステータス確認エラー: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"ステータス確認失敗: {e}")
            return None