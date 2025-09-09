import json
import os
import openai
import google.generativeai as genai
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step09: AI会話生成"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step09 開始: {lv_value}")
        
        # 1. AI会話生成機能が有効か確認
        if not config["ai_features"].get("enable_ai_conversation", False):
            print("AI会話生成機能が無効です。処理をスキップします。")
            return {"conversation_generated": False, "reason": "feature_disabled"}
        
        # 2. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. 統合JSONファイル読み込み
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        
        # 4. API設定確認
        ai_model = config["api_settings"]["ai_model"]
        if ai_model == "openai-gpt4o":
            api_key = config["api_settings"].get("openai_api_key", "")
            if not api_key:
                print("OpenAI API Keyが設定されていません。会話生成をスキップします。")
                return {"conversation_generated": False, "reason": "no_openai_key"}
        elif ai_model == "google-gemini-2.5-flash":
            api_key = config["api_settings"].get("google_api_key", "")
            if not api_key:
                print("Google API Keyが設定されていません。会話生成をスキップします。")
                return {"conversation_generated": False, "reason": "no_google_key"}
        else:
            print(f"未対応のAIモデル: {ai_model}")
            return {"conversation_generated": False, "reason": "unsupported_model"}
        
        # 5. 開始前会話生成
        intro_chat = generate_intro_conversation(broadcast_data, config, ai_model)
        
        # 6. 終了後会話生成
        outro_chat = generate_outro_conversation(broadcast_data, config, ai_model)
        
        # 7. 統合JSONに結果を追加
        if intro_chat:
            broadcast_data['intro_chat'] = intro_chat
        if outro_chat:
            broadcast_data['outro_chat'] = outro_chat
        
        # 会話生成時刻を記録
        broadcast_data['conversation_generated_at'] = datetime.now().isoformat()
        
        save_broadcast_data(broadcast_dir, lv_value, broadcast_data)
        
        print(f"Step09 完了: {lv_value} - 開始前会話: {len(intro_chat) if intro_chat else 0}発言, 終了後会話: {len(outro_chat) if outro_chat else 0}発言")
        return {
            "conversation_generated": True, 
            "intro_chat_count": len(intro_chat) if intro_chat else 0,
            "outro_chat_count": len(outro_chat) if outro_chat else 0,
            "model_used": ai_model
        }
        
    except Exception as e:
        print(f"Step09 エラー: {str(e)}")
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

def generate_intro_conversation(broadcast_data, config, ai_model):
    """開始前会話生成"""
    try:
        print("開始前会話生成中...")
        
        # プロンプト設定取得
        ai_prompts = config.get("ai_prompts", {})
        intro_prompt = ai_prompts.get("intro_conversation_prompt", "配信開始前の会話として、以下の内容について話し合います:")
        
        # キャラクター設定取得
        char1_name = ai_prompts.get("character1_name", "ニニちゃん")
        char1_personality = ai_prompts.get("character1_personality", "ボケ役で標準語を話す明るい女の子")
        char2_name = ai_prompts.get("character2_name", "ココちゃん")
        char2_personality = ai_prompts.get("character2_personality", "ツッコミ役で関西弁を話すしっかり者の女の子")
        conversation_turns = ai_prompts.get("conversation_turns", 5)
        
        # システムプロンプト作成
        system_prompt = create_system_prompt(char1_name, char1_personality, char2_name, char2_personality, conversation_turns)
        
        # ユーザープロンプト作成
        previous_summary = broadcast_data.get('previous_summary', '')
        live_title = broadcast_data.get('live_title', 'タイトル不明')
        broadcaster = broadcast_data.get('broadcaster', '配信者')  # 配信者名を取得
        
        if previous_summary.strip():
            # 前回放送がある場合
            user_prompt = f"""{intro_prompt}

配信者: {broadcaster}さん

前回の放送内容:
{previous_summary}

今回の放送タイトル: {live_title}

上記の情報を元に、{broadcaster}さんの前回の放送を振り返りつつ、今回の放送への期待を語る会話を作成してください。"""
        else:
            # 初回放送の場合
            user_prompt = f"""{intro_prompt}

配信者: {broadcaster}さん

今回の放送タイトル: {live_title}

これが{broadcaster}さんの初回の配信です。初めての配信への期待や緊張感を込めた会話を作成してください。"""
        
        # AI呼び出し
        conversation = call_ai_api(system_prompt, user_prompt, config, ai_model)
        
        if conversation:
            print("開始前会話生成完了")
            return conversation
        else:
            print("開始前会話生成失敗")
            return []
            
    except Exception as e:
        print(f"開始前会話生成エラー: {str(e)}")
        return []

def generate_outro_conversation(broadcast_data, config, ai_model):
    """終了後会話生成"""
    try:
        print("終了後会話生成中...")
        
        # 要約テキストの確認
        summary_text = broadcast_data.get('summary_text', '')
        if not summary_text.strip():
            print("要約テキストが見つかりません。終了後会話生成をスキップします。")
            return []
        
        # プロンプト設定取得
        ai_prompts = config.get("ai_prompts", {})
        outro_prompt = ai_prompts.get("outro_conversation_prompt", "配信終了後の振り返りとして、以下の内容について話し合います:")
        
        # キャラクター設定取得
        char1_name = ai_prompts.get("character1_name", "ニニちゃん")
        char1_personality = ai_prompts.get("character1_personality", "ボケ役で標準語を話す明るい女の子")
        char2_name = ai_prompts.get("character2_name", "ココちゃん")
        char2_personality = ai_prompts.get("character2_personality", "ツッコミ役で関西弁を話すしっかり者の女の子")
        conversation_turns = ai_prompts.get("conversation_turns", 5)
        
        # システムプロンプト作成
        system_prompt = create_system_prompt(char1_name, char1_personality, char2_name, char2_personality, conversation_turns)
        
        # ユーザープロンプト作成
        live_title = broadcast_data.get('live_title', 'タイトル不明')
        broadcaster = broadcast_data.get('broadcaster', '配信者')  # 配信者名を取得
        
        user_prompt = f"""{outro_prompt}

配信者: {broadcaster}さん

今回の放送内容:
{summary_text}

放送タイトル: {live_title}

上記の{broadcaster}さんの放送内容を振り返って、感想や印象に残ったことを語り合う会話を作成してください。"""
        
        # AI呼び出し
        conversation = call_ai_api(system_prompt, user_prompt, config, ai_model)
        
        if conversation:
            print("終了後会話生成完了")
            return conversation
        else:
            print("終了後会話生成失敗")
            return []
            
    except Exception as e:
        print(f"終了後会話生成エラー: {str(e)}")
        return []

def create_system_prompt(char1_name, char1_personality, char2_name, char2_personality, conversation_turns):
    """システムプロンプト作成"""
    return f"""あなたは二人のキャラクターによる自然な会話を生成するAIです。

キャラクター1: {char1_name}
性格: {char1_personality}

キャラクター2: {char2_name}
性格: {char2_personality}

指示:
- 二人の自然で楽しい会話を{conversation_turns}往復（計{conversation_turns * 2}発言）で作成してください
- 各キャラクターの性格と話し方を一貫して維持してください
- 会話は自然な流れで、お互いに反応し合うようにしてください
- 結果は必ずJSON形式で返してください
- JSONマーカー（```json）は使用しないでください

JSON形式:
{{"conversation": [{{"name": "キャラクター名", "dialogue": "セリフ"}}]}}"""

def call_ai_api(system_prompt, user_prompt, config, ai_model):
    """AI API呼び出し（OpenAIまたはGoogle）"""
    try:
        if ai_model == "openai-gpt4o":
            return call_openai_api(system_prompt, user_prompt, config)
        elif ai_model == "google-gemini-2.5-flash":
            return call_google_api(system_prompt, user_prompt, config)
        else:
            raise Exception(f"未対応のAIモデル: {ai_model}")
            
    except Exception as e:
        print(f"AI API呼び出しエラー: {str(e)}")
        return []

def call_openai_api(system_prompt, user_prompt, config):
    """OpenAI API呼び出し"""
    try:
        api_key = config["api_settings"]["openai_api_key"]
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,
            temperature=0.8
        )
        
        response_text = response.choices[0].message.content.strip()
        return parse_conversation_json(response_text)
        
    except Exception as e:
        print(f"OpenAI API呼び出しエラー: {str(e)}")
        return []

def call_google_api(system_prompt, user_prompt, config):
    """Google Gemini API呼び出し"""
    try:
        api_key = config["api_settings"]["google_api_key"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # システムプロンプトとユーザープロンプトを結合
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        response = model.generate_content(
            combined_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2000,
                temperature=0.8
            )
        )
        
        response_text = response.text.strip()
        return parse_conversation_json(response_text)
        
    except Exception as e:
        print(f"Google API呼び出しエラー: {str(e)}")
        return []

def parse_conversation_json(response_text):
    """AI応答からJSON会話データを解析"""
    try:
        # JSONマーカーを除去
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        # JSON解析
        conversation_data = json.loads(response_text)
        
        # 会話データの検証
        if isinstance(conversation_data, dict) and 'conversation' in conversation_data:
            conversation_list = conversation_data['conversation']
            if isinstance(conversation_list, list):
                # 各会話項目を検証
                valid_conversation = []
                for item in conversation_list:
                    if isinstance(item, dict) and 'name' in item and 'dialogue' in item:
                        valid_conversation.append({
                            'name': str(item['name']),
                            'dialogue': str(item['dialogue'])
                        })
                
                print(f"会話解析成功: {len(valid_conversation)}発言")
                return valid_conversation
        
        print("会話データの形式が不正です")
        return []
        
    except json.JSONDecodeError as e:
        print(f"JSON解析エラー: {str(e)}")
        print(f"応答テキスト: {response_text[:200]}...")
        return []
    except Exception as e:
        print(f"会話解析エラー: {str(e)}")
        return []