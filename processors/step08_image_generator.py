import json
import os
import openai
import requests
import base64
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step08: AI画像生成"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step08 開始: {lv_value}")
        
        # 1. AI画像生成機能が有効か確認
        if not config["ai_features"].get("enable_summary_image", False):
            print("AI画像生成機能が無効です。処理をスキップします。")
            return {"image_generated": False, "reason": "feature_disabled"}
        
        # 2. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. 統合JSONファイル読み込み
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        
        # 4. 要約テキストの確認
        summary_text = broadcast_data.get('summary_text', '')
        if not summary_text.strip():
            print("要約テキストが見つかりません。画像生成をスキップします。")
            return {"image_generated": False, "reason": "no_summary"}
        
        # 5. OpenAI API設定確認
        openai_api_key = config["api_settings"].get("openai_api_key", "")
        if not openai_api_key:
            print("OpenAI API Keyが設定されていません。画像生成をスキップします。")
            return {"image_generated": False, "reason": "no_openai_key"}
        
        # 6. Imgur API設定確認
        imgur_api_key = config["api_settings"].get("imgur_api_key", "")
        if not imgur_api_key:
            print("Imgur API Keyが設定されていません。画像生成をスキップします。")
            return {"image_generated": False, "reason": "no_imgur_key"}
        
        # 7. 画像生成
        image_result = generate_image_from_summary(
            broadcast_data.get('live_title', 'タイトル不明'),
            summary_text,
            openai_api_key,
            imgur_api_key,
            config["ai_prompts"].get("image_prompt", "次の文章は、ある生放送の要約です。この生放送の抽象的なイメージを生成してください:")
        )
        
        if image_result:
            # 8. 統合JSONに結果を追加
            broadcast_data['image_generation'] = image_result
            save_broadcast_data(broadcast_dir, lv_value, broadcast_data)
            
            print(f"Step08 完了: {lv_value} - 画像生成成功")
            return {"image_generated": True, "image_url": image_result.get("imgur_url")}
        else:
            print(f"Step08 完了: {lv_value} - 画像生成失敗")
            return {"image_generated": False, "reason": "generation_failed"}
        
    except Exception as e:
        print(f"Step08 エラー: {str(e)}")
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

def generate_image_from_summary(title, summary, openai_api_key, imgur_api_key, image_prompt):
    """要約から画像を生成してImgurにアップロード"""
    try:
        print(f"画像生成開始: {title}")
        print(f"要約: {summary[:100]}...")
        
        # 1. DALL-E用プロンプト作成
        dalle_prompt = create_dalle_prompt(title, summary, image_prompt)
        print(f"DALL-E プロンプト: {dalle_prompt}")
        
        # 2. DALL-E で画像生成
        image_url = generate_dalle_image(dalle_prompt, openai_api_key)
        if not image_url:
            return None
        
        # 3. 画像をダウンロード
        image_data = download_image(image_url)
        if not image_data:
            return None
        
        # 4. Imgurにアップロード
        imgur_url = upload_to_imgur(image_data, imgur_api_key, title)
        if not imgur_url:
            return None
        
        return {
            "dalle_url": image_url,
            "imgur_url": imgur_url,
            "dalle_prompt": dalle_prompt,
            "generated_at": datetime.now().isoformat(),
            "title": title
        }
        
    except Exception as e:
        print(f"画像生成エラー: {str(e)}")
        return None

def create_dalle_prompt(title, summary, base_prompt):
    """要約からDALL-E用プロンプトを作成"""
    # 要約を短縮して視覚的な表現に変換
    prompt_parts = [base_prompt]
    
    # 基本的なスタイル指定
    prompt_parts.append("Abstract digital art style")
    
    # 要約の内容に基づいて視覚的要素を決定
    if any(word in summary.lower() for word in ['ゲーム', 'game', 'プレイ']):
        prompt_parts.append("with gaming elements and vibrant colors")
    elif any(word in summary.lower() for word in ['政治', '社会', '議論']):
        prompt_parts.append("with serious tones and geometric shapes")
    elif any(word in summary.lower() for word in ['音楽', 'music', '楽曲']):
        prompt_parts.append("with musical notes and flowing waves")
    elif any(word in summary.lower() for word in ['技術', 'tech', 'AI', 'プログラム']):
        prompt_parts.append("with futuristic and technological elements")
    else:
        prompt_parts.append("with soft gradients and warm colors")
    
    # タイトルの要素を追加
    prompt_parts.append(f"representing the theme of '{title}'")
    
    # 要約の重要キーワードを抽出（最初の50文字から）
    key_content = summary[:100].replace('\n', ' ')
    prompt_parts.append(f"inspired by: {key_content}")
    
    return ", ".join(prompt_parts)

def generate_dalle_image(prompt, api_key):
    """DALL-E 3で画像生成"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        print(f"DALL-E 画像生成成功: {image_url}")
        return image_url
        
    except Exception as e:
        print(f"DALL-E 画像生成エラー: {str(e)}")
        return None

def download_image(url):
    """画像をダウンロード"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print(f"画像ダウンロード成功: {len(response.content)} bytes")
        return response.content
        
    except Exception as e:
        print(f"画像ダウンロードエラー: {str(e)}")
        return None

def upload_to_imgur(image_data, api_key, title):
    """ImgurにアップロードしてURLを取得"""
    try:
        headers = {
            'Authorization': f'Client-ID {api_key}',
        }
        
        # Base64エンコード
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        data = {
            'image': image_b64,
            'type': 'base64',
            'title': title,
            'description': f'AI generated image for broadcast: {title}'
        }
        
        response = requests.post(
            'https://api.imgur.com/3/image',
            headers=headers,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                imgur_url = result['data']['link']
                print(f"Imgur アップロード成功: {imgur_url}")
                return imgur_url
            else:
                print(f"Imgur アップロード失敗: {result}")
                return None
        else:
            print(f"Imgur API エラー {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Imgur アップロードエラー: {str(e)}")
        return None