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
        
        # 要約テキストをそのまま歌詞として使用
        lyrics = create_music_prompt(summary)
        
        # 音楽生成実行
        result = suno_api.generate_music(
            prompt=lyrics,
            custom_mode=True,
            instrumental=False,
            model="V4",
            style="J-Pop, Ballad",
            title=title
        )
        
        if result:
            return {
                "task_id": result["task_id"],
                "songs": result["songs"],
                "music_prompt": lyrics,
                "generated_at": datetime.now().isoformat(),
                "title": title,
                "status": result.get("status", "generated")
            }
        
        return None
        
    except Exception as e:
        print(f"音楽生成エラー: {str(e)}")
        return None

def create_music_prompt(summary):
    """要約テキストを歌詞として使用（V4は最大3000文字）"""
    lyrics = summary[:3000] if len(summary) > 3000 else summary
    return lyrics

class SunoAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.sunoapi.org/api/v1"
        self.generate_url = f"{self.base_url}/generate"
        self.details_url = f"{self.base_url}/generate/record-info"
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
                      model="V4", style=None, title=None):
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
                self.generate_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") != 200 or not result.get("data"):
                    print("API did not return taskId properly")
                    return None
                    
                task_id = result["data"]["taskId"]
                print(f"音楽生成開始 - TaskID: {task_id}")
                
                # 完了まで待機してURLを取得
                songs = self._wait_for_completion(task_id)
                if songs:
                    return {
                        "task_id": task_id,
                        "songs": songs,
                        "status": "ready"
                    }
                return None
                
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
    
    def _wait_for_completion(self, task_id):
        """タスク完了まで待機して楽曲情報を取得"""
        print("生成を待機中...")
        
        for attempt in range(24):  # 最大4分待機
            time.sleep(10)
            print(f"   {(attempt+1)*10}秒経過...")
            
            self._rate_limit()
            try:
                response = requests.get(
                    self.details_url,
                    headers=self.headers,
                    params={"taskId": task_id},
                    timeout=30
                )
                
                if response.status_code != 200:
                    print(f"詳細取得エラー: {response.status_code}")
                    continue
                
                details_data = response.json()
                status = details_data.get("data", {}).get("status")
                print(f"現在のステータス: {status}")
                
                if status == "SUCCESS":
                    print("生成完了!")
                    songs = self._extract_valid_songs(details_data)
                    return songs
                    
                elif status in ["CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"]:
                    print(f"タスク失敗: {status}")
                    return None
                    
            except Exception as e:
                print(f"ステータス確認失敗: {e}")
                continue
        
        print("タイムアウト")
        return None
    
    def _extract_valid_songs(self, details_data):
        """楽曲データから有効なURLを持つ楽曲を抽出"""
        response_data = details_data.get("data", {})
        songs = response_data.get("response", {}).get("sunoData", [])
        
        if not songs:
            return []
        
        print(f"{len(songs)}曲が生成されました")
        valid_songs = []
        
        for i, song in enumerate(songs, 1):
            audio_urls = [
                song.get('audioUrl'),
                song.get('sourceAudioUrl'), 
                song.get('streamAudioUrl'),
                song.get('sourceStreamAudioUrl')
            ]
            
            valid_audio_urls = []
            for url in audio_urls:
                if url:
                    try:
                        head_response = requests.head(url, timeout=5)
                        if head_response.status_code == 200:
                            valid_audio_urls.append(url)
                    except:
                        pass
            
            if valid_audio_urls:
                song_info = {
                    'id': song.get('id'),
                    'title': song.get('title'),
                    'duration': song.get('duration'),
                    'urls': valid_audio_urls,
                    'primary_url': valid_audio_urls[0],
                    'image_url': song.get('imageUrl'),
                    'tags': song.get('tags'),
                    'model': song.get('modelName')
                }
                valid_songs.append(song_info)
        
        return valid_songs