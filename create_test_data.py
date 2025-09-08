import os
import json
from datetime import datetime
import xml.etree.ElementTree as ET

def create_test_directories():
    """テスト用ディレクトリを作成"""
    dirs = [
        "test_data/test123_user/lv999999999",
        "test_ncv",
        "config/users"
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 ディレクトリ作成: {dir_path}")

def create_test_user_config():
    """テストユーザー設定を作成"""
    test_config = {
        "account_id": "test123",
        "display_name": "テストユーザー",
        "basic_settings": {
            "platform": "niconico",
            "account_id": "test123",
            "platform_directory": "test_data",
            "ncv_directory": "test_ncv"
        },
        "api_settings": {
            "ai_model": "openai-gpt4o",
            "openai_api_key": "",
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
            "intro_conversation_prompt": "配信開始前の会話として、以下の内容について2人のAIが話します:",
            "outro_conversation_prompt": "配信終了後の振り返りとして、以下の内容について2人のAIが話します:",
            "image_prompt": "この配信の抽象的なイメージを生成してください:"
        },
        "display_features": {
            "enable_emotion_scores": True,
            "enable_comment_ranking": True,
            "enable_word_ranking": True,
            "enable_thumbnails": True,
            "enable_audio_player": True,
            "enable_timeshift_jump": True
        },
        "special_users": ["12345", "67890", "99999"],
        "last_updated": datetime.now().isoformat()
    }
    
    config_path = "config/users/test123.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    print(f"👤 テストユーザー設定作成: {config_path}")

def create_test_broadcast_json():
    """テスト用統合JSONを作成"""
    now = datetime.now()
    open_time = int(now.timestamp()) - 3600  # 1時間前
    start_time = open_time + 300  # 5分後
    end_time = start_time + 3600  # 1時間後
    server_time = start_time + 10  # 10秒遅れ
    
    broadcast_data = {
        "lv_value": "lv999999999",
        "timestamp": now.isoformat(),
        "server_time": str(server_time),
        "video_duration": 3600.0,
        "time_diff_seconds": 10,
        
        # ディレクトリパス
        "account_directory_path": os.path.abspath("test_data/test123_user"),
        "broadcast_directory_path": os.path.abspath("test_data/test123_user/lv999999999"),
        
        # XMLファイルパス
        "ncv_xml_path": os.path.abspath("test_ncv/lv999999999_comment.xml"),
        "platform_xml_path": os.path.abspath("test_ncv/lv999999999_comment.xml"),
        
        # NCVデータ
        "live_num": "999999999",
        "elapsed_time": "3600",
        "live_title": "【テスト配信】AIアーカイブシステムのテスト放送",
        "broadcaster": "テスト配信者",
        "default_community": "co999999",
        "community_name": "テストコミュニティ",
        "open_time": str(open_time),
        "start_time": str(start_time),
        "end_time": str(end_time),
        "watch_count": "1234",
        "comment_count": "567",
        "owner_id": "test123",
        "owner_name": "テスト配信者",
        
        # 前回放送情報
        "previous_summary": "前回の配信では、新機能のテストを行いました。視聴者からは好評の声が多く寄せられました。",
        
        # AI処理結果（初期状態）
        "summary_text": "",
        "intro_chat": [],
        "outro_chat": [],
        
        # 感情分析統計（サンプル）
        "sentiment_stats": {
            "avg_center": 0.45,
            "avg_positive": 0.35,
            "avg_negative": 0.20,
            "max_center": 0.78,
            "max_positive": 0.89,
            "max_negative": 0.67,
            "max_center_time": 1800,
            "max_positive_time": 2400,
            "max_negative_time": 900,
            "total_segments": 120
        },
        
        # 単語ランキング（サンプル）
        "word_ranking": [
            {"rank": 1, "word": "テスト", "count": 45, "font_size": 49},
            {"rank": 2, "word": "配信", "count": 38, "count": 48},
            {"rank": 3, "word": "システム", "count": 32, "font_size": 47},
            {"rank": 4, "word": "機能", "count": 28, "font_size": 46},
            {"rank": 5, "word": "視聴者", "count": 25, "font_size": 45}
        ]
    }
    
    json_path = "test_data/test123_user/lv999999999/lv999999999_data.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
    
    print(f"📊 統合JSON作成: {json_path}")

def create_test_transcript_json():
    """テスト用文字起こしJSONを作成"""
    transcript_data = {
        "lv_value": "lv999999999",
        "total_segments": 10,
        "creation_time": datetime.now().isoformat(),
        "transcripts": [
            {
                "timestamp": 30,
                "text": "皆さんこんにちは、テスト配信を開始します",
                "positive_score": 0.7,
                "center_score": 0.2,
                "negative_score": 0.1
            },
            {
                "timestamp": 65,
                "text": "今日は新しいAIアーカイブシステムのテストを行います",
                "positive_score": 0.6,
                "center_score": 0.3,
                "negative_score": 0.1
            },
            {
                "timestamp": 120,
                "text": "システムが正常に動作するかチェックしていきましょう",
                "positive_score": 0.5,
                "center_score": 0.4,
                "negative_score": 0.1
            },
            {
                "timestamp": 180,
                "text": "音声認識の精度はどうでしょうか",
                "positive_score": 0.3,
                "center_score": 0.6,
                "negative_score": 0.1
            },
            {
                "timestamp": 240,
                "text": "コメントもしっかり取得できているようですね",
                "positive_score": 0.8,
                "center_score": 0.1,
                "negative_score": 0.1
            },
            {
                "timestamp": 300,
                "text": "感情分析の結果も興味深いです",
                "positive_score": 0.6,
                "center_score": 0.3,
                "negative_score": 0.1
            },
            {
                "timestamp": 360,
                "text": "単語頻度の分析も機能していますね",
                "positive_score": 0.5,
                "center_score": 0.4,
                "negative_score": 0.1
            },
            {
                "timestamp": 420,
                "text": "これでテストは一通り完了でしょうか",
                "positive_score": 0.4,
                "center_score": 0.5,
                "negative_score": 0.1
            },
            {
                "timestamp": 480,
                "text": "視聴してくださった皆さん、ありがとうございました",
                "positive_score": 0.9,
                "center_score": 0.05,
                "negative_score": 0.05
            },
            {
                "timestamp": 540,
                "text": "それではまた次回の配信でお会いしましょう",
                "positive_score": 0.8,
                "center_score": 0.15,
                "negative_score": 0.05
            }
        ]
    }
    
    json_path = "test_data/test123_user/lv999999999/lv999999999_transcript.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)
    
    print(f"📝 文字起こしJSON作成: {json_path}")

def create_test_ncv_xml():
    """テスト用NCVのXMLファイルを作成"""
    root = ET.Element("CommentLog")
    root.set("server_time", str(int(datetime.now().timestamp())))
    
    # LiveInfo
    live_info = ET.SubElement(root, "LiveInfo")
    ET.SubElement(live_info, "LiveNum").text = "999999999"
    ET.SubElement(live_info, "LiveTitle").text = "【テスト配信】AIアーカイブシステムのテスト放送"
    ET.SubElement(live_info, "Broadcaster").text = "テスト配信者"
    ET.SubElement(live_info, "DefaultCommunity").text = "co999999"
    ET.SubElement(live_info, "CommunityName").text = "テストコミュニティ"
    ET.SubElement(live_info, "OpenTime").text = str(int(datetime.now().timestamp()) - 3600)
    ET.SubElement(live_info, "StartTime").text = str(int(datetime.now().timestamp()) - 3300)
    ET.SubElement(live_info, "EndTime").text = str(int(datetime.now().timestamp()) - 300)
    
    # PlayerStatus
    player_status = ET.SubElement(root, "PlayerStatus")
    ET.SubElement(player_status, "WatchCount").text = "1234"
    ET.SubElement(player_status, "CommentCount").text = "567"
    ET.SubElement(player_status, "OwnerId").text = "test123"
    ET.SubElement(player_status, "OwnerName").text = "テスト配信者"
    
    # LiveCommentDataArray
    comment_array = ET.SubElement(root, "LiveCommentDataArray")
    
    # サンプルコメント
    comments = [
        {"no": "1", "date": str(int(datetime.now().timestamp()) - 3000), "vpos": "3000", "user_id": "12345", "name": "視聴者A", "text": "テスト配信お疲れ様です！"},
        {"no": "2", "date": str(int(datetime.now().timestamp()) - 2800), "vpos": "5000", "user_id": "67890", "name": "視聴者B", "text": "システムすごいですね"},
        {"no": "3", "date": str(int(datetime.now().timestamp()) - 2600), "vpos": "7000", "user_id": "99999", "name": "スペシャルユーザー", "text": "特別なコメントです"},
        {"no": "4", "date": str(int(datetime.now().timestamp()) - 2400), "vpos": "9000", "user_id": "a:anonymous1", "name": "", "text": "匿名コメント"},
        {"no": "5", "date": str(int(datetime.now().timestamp()) - 2200), "vpos": "11000", "user_id": "12345", "name": "視聴者A", "text": "感情分析はどうなりますかね？"},
    ]
    
    for comment in comments:
        chat = ET.SubElement(comment_array, "chat")
        chat.set("no", comment["no"])
        chat.set("date", comment["date"])
        chat.set("vpos", comment["vpos"])
        chat.set("user_id", comment["user_id"])
        chat.set("name", comment["name"])
        chat.text = comment["text"]
    
    # XMLファイル保存
    tree = ET.ElementTree(root)
    xml_path = "test_ncv/lv999999999_comment.xml"
    tree.write(xml_path, encoding='utf-8', xml_declaration=True)
    
    print(f"📄 NCVのXML作成: {xml_path}")

def create_test_html():
    """テスト用HTMLファイルを作成"""
    html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>【テスト配信】AIアーカイブシステムのテスト放送 - ニコニコ生放送</title>
</head>
<body>
    <h1>【テスト配信】AIアーカイブシステムのテスト放送</h1>
    <p>配信者: テスト配信者</p>
    <p>コミュニティ: テストコミュニティ</p>
    <p>これはテスト用のHTMLファイルです。</p>
</body>
</html>"""
    
    html_path = "test_data/test123_user/lv999999999/lv999999999.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"🌐 HTML作成: {html_path}")

def main():
    """メイン処理"""
    print("🚀 テストデータ作成開始")
    print("="*50)
    
    create_test_directories()
    create_test_user_config()
    create_test_broadcast_json()
    create_test_transcript_json()
    create_test_ncv_xml()
    create_test_html()
    
    print("="*50)
    print("✅ テストデータ作成完了！")
    print("\n📋 作成されたファイル:")
    print("  - config/users/test123.json")
    print("  - test_data/test123_user/lv999999999/lv999999999_data.json")
    print("  - test_data/test123_user/lv999999999/lv999999999_transcript.json")
    print("  - test_data/test123_user/lv999999999/lv999999999.html")
    print("  - test_ncv/lv999999999_comment.xml")
    print("\n🎯 テスト実行方法:")
    print("  python test_steps.py")

if __name__ == "__main__":
    main()