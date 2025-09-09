import time
import requests
import os
import json
import webbrowser

API_KEY = "32f0ac7aca210ab3d84d94e3b5393d6c"
GENERATE_URL = "https://api.sunoapi.org/api/v1/generate"
DETAILS_URL = "https://api.sunoapi.org/api/v1/generate/record-info"

payload = {
    "customMode": True,
    "instrumental": False,
    "model": "V4",
    "title": "春の風",
    "style": "J-Pop, Acoustic",
    "prompt": """桜咲く道を歩いて
新しい季節が始まる
君と過ごした日々を思い出して
心に温かい風が吹く

ラララ 春の風よ
運んでおくれ この想いを
ラララ 青い空に
希望の歌を響かせて

変わりゆく街角で
出会いと別れを繰り返し
でも忘れない あの笑顔を
いつまでも大切にしていこう

ラララ 春の風よ
運んでおくれ この想いを
ラララ 青い空に
希望の歌を響かせて

新しい扉を開けて
歩いていこう 未来へと""",
    "vocalGender": "f",
    "callBackUrl": "https://example.com/callback"
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Step 1: 曲生成リクエスト
print("🎵 楽曲生成を開始...")
response = requests.post(GENERATE_URL, headers=headers, data=json.dumps(payload))
print("ステータスコード:", response.status_code)

if response.status_code != 200:
    print("エラーレスポンス:", response.text)
    raise Exception("Generate Music API request failed")

data = response.json()
if data.get("code") != 200 or not data.get("data"):
    raise Exception("API did not return taskId properly")

task_id = data["data"]["taskId"]
print(f"✓ タスクID: {task_id}")

# Step 2: タスク完了までポーリング
print("⏳ 生成を待機中...")
while True:
    details_response = requests.get(
        DETAILS_URL,
        headers=headers,
        params={"taskId": task_id}
    )
    
    if details_response.status_code != 200:
        print("詳細取得エラー:", details_response.text)
        time.sleep(10)
        continue
    
    details_data = details_response.json()
    status = details_data.get("data", {}).get("status")
    print(f"現在のステータス: {status}")
    
    if status == "SUCCESS":
        print("✅ 生成完了!")
        break
    elif status in ["CREATE_TASK_FAILED", "GENERATE_AUDIO_FAILED", "CALLBACK_EXCEPTION", "SENSITIVE_WORD_ERROR"]:
        print("詳細レスポンス:", json.dumps(details_data, indent=2, ensure_ascii=False))
        raise Exception(f"タスク失敗: {status}")
    
    time.sleep(10)

# Step 3: 正しいURL構造でURLを取得
print("\n🎶 楽曲URLを取得中...")
response_data = details_data.get("data", {})
songs = response_data.get("response", {}).get("sunoData", [])

if not songs:
    raise Exception("楽曲データが見つかりません")

print(f"✓ {len(songs)}曲が生成されました")

# 各楽曲の情報を表示して有効なURLを収集
valid_songs = []
for i, song in enumerate(songs, 1):
    print(f"\n--- 楽曲 {i} ---")
    print(f"ID: {song.get('id')}")
    print(f"タイトル: {song.get('title')}")
    print(f"長さ: {song.get('duration')}秒")
    print(f"モデル: {song.get('modelName')}")
    
    # 利用可能なオーディオURLをテスト
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
                    print(f"✓ 有効なURL: {url}")
            except:
                pass
    
    if valid_audio_urls:
        song_info = {
            'id': song.get('id'),
            'title': song.get('title'),
            'duration': song.get('duration'),
            'urls': valid_audio_urls,
            'image_url': song.get('imageUrl'),
            'tags': song.get('tags')
        }
        valid_songs.append(song_info)

# Step 4: HTMLファイル作成
if valid_songs:
    print(f"\n🌸 HTMLファイルを作成中...")
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>春の風 - Suno AI Generated Music</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #ffeef7, #e8f4f8);
            min-height: 100vh;
        }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #ff6b9d; text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .lyrics {{ 
            background: linear-gradient(45deg, #f5f5f5, #fafafa); 
            padding: 20px; 
            border-radius: 10px; 
            white-space: pre-line; 
            border-left: 4px solid #ff6b9d;
            font-size: 1.1em;
            line-height: 1.6;
            margin-bottom: 30px;
        }}
        .song-container {{ 
            background: #f8f9fa; 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 10px; 
            border: 2px solid #e9ecef;
        }}
        .song-title {{ color: #333; font-size: 1.3em; margin-bottom: 10px; }}
        .song-info {{ color: #666; margin-bottom: 15px; font-size: 0.9em; }}
        audio {{ 
            width: 100%; 
            margin-bottom: 15px;
            border-radius: 5px;
        }}
        .url-list {{ 
            background: #e8f4f8; 
            padding: 15px; 
            border-radius: 8px; 
            margin-top: 20px;
        }}
        .url-list h4 {{ margin-top: 0; color: #0066cc; }}
        .url-list li {{ margin: 5px 0; }}
        .url-list a {{ color: #0066cc; text-decoration: none; }}
        .url-list a:hover {{ text-decoration: underline; }}
        .generation-info {{ 
            background: #fff3cd; 
            padding: 15px; 
            border-radius: 8px; 
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌸 春の風</h1>
        <div class="subtitle">J-Pop, Acoustic • Model: V4 • Generated by Suno AI</div>
        
        <div class="generation-info">
            <strong>🎵 生成情報:</strong><br>
            タスクID: {task_id}<br>
            生成楽曲数: {len(valid_songs)}曲<br>
            スタイル: J-Pop, Acoustic
        </div>
        
        <h3>📝 歌詞:</h3>
        <div class="lyrics">桜咲く道を歩いて
新しい季節が始まる
君と過ごした日々を思い出して
心に温かい風が吹く

ラララ 春の風よ
運んでおくれ この想いを
ラララ 青い空に
希望の歌を響かせて

変わりゆく街角で
出会いと別れを繰り返し
でも忘れない あの笑顔を
いつまでも大切にしていこう

ラララ 春の風よ
運んでおくれ この想いを
ラララ 青い空に
希望の歌を響かせて

新しい扉を開けて
歩いていこう 未来へと</div>
"""

    # 各楽曲のプレーヤーを追加
    for i, song in enumerate(valid_songs, 1):
        html_content += f"""
        <div class="song-container">
            <div class="song-title">🎵 バージョン {i}</div>
            <div class="song-info">
                長さ: {song['duration']}秒 • ID: {song['id'][:8]}...
            </div>
            <audio controls preload="auto">
                <source src="{song['urls'][0]}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            
            <details>
                <summary>利用可能なURL ({len(song['urls'])}個)</summary>
                <ul style="margin: 10px 0;">
"""
        for url in song['urls']:
            html_content += f'<li><a href="{url}" target="_blank">{url}</a></li>\n'
        
        html_content += """
                </ul>
            </details>
        </div>
"""

    html_content += """
    </div>
    
    <script>
        // 各オーディオ要素にイベントリスナーを追加
        document.querySelectorAll('audio').forEach((audio, index) => {
            audio.addEventListener('loadstart', () => {
                console.log(`🎵 楽曲${index + 1} 読み込み開始...`);
            });
            
            audio.addEventListener('canplay', () => {
                console.log(`✓ 楽曲${index + 1} 再生準備完了`);
            });
            
            audio.addEventListener('error', (e) => {
                console.error(`✗ 楽曲${index + 1} 読み込みエラー:`, e);
                alert(`楽曲${index + 1}の読み込みに失敗しました。URLを直接クリックして試してください。`);
            });
        });
        
        // 最初の楽曲の自動再生を試行
        const firstAudio = document.querySelector('audio');
        if (firstAudio) {
            firstAudio.addEventListener('canplay', () => {
                firstAudio.play().catch(e => {
                    console.log('自動再生はブラウザによってブロックされました。手動で再生してください。');
                });
            }, { once: true });
        }
    </script>
</body>
</html>
"""
    
    html_path = f"春の風_{task_id[:8]}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    abs_path = os.path.abspath(html_path)
    print(f"✅ HTMLファイル作成完了: {abs_path}")
    webbrowser.open("file://" + abs_path)
    
    print(f"\n🎉 成功！{len(valid_songs)}曲の日本語楽曲が生成されました！")
    
else:
    print("❌ 有効な楽曲が見つかりませんでした")