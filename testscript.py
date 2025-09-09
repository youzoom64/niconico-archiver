#!/usr/bin/env python3
import requests
import base64
import os
from pathlib import Path

CLIENT_ID = "49399fc1d98876a"

def upload_image_to_imgur(image_path):
    """画像をImgurにアップロードする"""
    
    # 画像ファイルの存在確認
    if not os.path.exists(image_path):
        print(f"エラー: ファイルが見つかりません - {image_path}")
        return None
    
    # 画像をBase64エンコード
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    
    # APIリクエスト
    url = "https://api.imgur.com/3/image"
    headers = {
        "Authorization": f"Client-ID {CLIENT_ID}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "image": image_data,
        "type": "base64",
        "title": f"Upload from script - {Path(image_path).name}",
        "description": "Uploaded via Python script"
    }
    
    print(f"アップロード中: {image_path}")
    print("=" * 40)
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                image_info = data['data']
                print("✅ アップロード成功!")
                print(f"画像URL: {image_info['link']}")
                print(f"削除ハッシュ: {image_info['deletehash']}")
                print(f"画像ID: {image_info['id']}")
                return image_info
            else:
                print("❌ アップロード失敗")
                print(f"エラー: {data}")
        else:
            print("❌ APIエラー")
            print(f"レスポンス: {response.text}")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
    
    return None

def main():
    # テスト用画像パスを指定（適宜変更してください）
    test_images = [
        "test.jpg",
        "sample.png", 
        "image.gif",
        "screenshot.png"
    ]
    
    # 存在する画像ファイルを探してアップロード
    uploaded = False
    for image_path in test_images:
        if os.path.exists(image_path):
            result = upload_image_to_imgur(image_path)
            if result:
                uploaded = True
                break
    
    if not uploaded:
        print("テスト用画像が見つかりません。")
        print("以下のいずれかの画像ファイルを同じディレクトリに配置してください:")
        for img in test_images:
            print(f"  - {img}")
        
        # 手動でパスを指定
        custom_path = input("\n画像ファイルのパスを入力してください（Enterでスキップ）: ").strip()
        if custom_path:
            upload_image_to_imgur(custom_path)

if __name__ == "__main__":
    main()