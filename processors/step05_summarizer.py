import json
import os
import openai
import google.generativeai as genai
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step05: AI要約生成"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step05 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. transcript.jsonから本文抽出
        transcript_text = extract_transcript_text(broadcast_dir, lv_value)
        if not transcript_text.strip():
            print("文字起こしテキストが空です")
            return {"summary": ""}
        
        # 3. AI要約生成
        ai_model = config["api_settings"]["summary_ai_model"]  # 要約専用モデル
        summary = generate_summary(transcript_text, config, ai_model)
        
        # 4. 統合JSONに要約を追加
        update_broadcast_json(broadcast_dir, lv_value, summary)
        
        # 5. 要約テキストファイル保存
        save_summary_text(broadcast_dir, lv_value, summary)
        
        print(f"Step05 完了: {lv_value} - 要約文字数: {len(summary)}")
        return {"summary": summary, "model_used": ai_model}
        
    except Exception as e:
        print(f"Step05 エラー: {str(e)}")
        raise

def extract_transcript_text(broadcast_dir, lv_value):
    """transcript.jsonから本文のみを抽出"""
    try:
        transcript_path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
        if not os.path.exists(transcript_path):
            raise Exception(f"transcript.jsonが見つかりません: {transcript_path}")
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcripts = transcript_data.get('transcripts', [])
        
        # 本文のみを抽出して結合
        text_segments = []
        for segment in transcripts:
            text = segment.get('text', '').strip()
            if text:
                text_segments.append(text)
        
        full_text = '\n'.join(text_segments)
        print(f"抽出したテキスト文字数: {len(full_text)}")
        
        return full_text
        
    except Exception as e:
        print(f"テキスト抽出エラー: {str(e)}")
        raise

def generate_summary(text, config, ai_model):
    """AIを使用して要約生成"""
    try:
        summary_prompt = config["ai_prompts"]["summary_prompt"]
        
        # テキストが長すぎる場合は分割処理
        max_chunk_size = 8000  # 安全なチャンクサイズ
        
        if len(text) <= max_chunk_size:
            # 短いテキストはそのまま処理
            return generate_summary_single(text, summary_prompt, config, ai_model)
        else:
            # 長いテキストは分割して処理
            return generate_summary_chunked(text, summary_prompt, config, ai_model, max_chunk_size)
        
    except Exception as e:
        print(f"要約生成エラー: {str(e)}")
        raise

def generate_summary_single(text, prompt, config, ai_model):
    """単一テキストの要約生成"""
    try:
        full_prompt = f"{prompt}\n\n{text}"
        print(f"[DEBUG] generate_summary_single: モデル={ai_model}, prompt文字数={len(full_prompt)}")
        
        if ai_model == "openai-gpt4o":
            print("[DEBUG] OpenAI GPT-4o APIを呼び出します")
            return call_openai_api(full_prompt, config)
        elif ai_model == "google-gemini-2.5-flash":
            print("[DEBUG] Google Gemini 2.5 Flash APIを呼び出します")
            return call_google_api(full_prompt, config)
        else:
            raise Exception(f"未対応のAIモデル: {ai_model}")
            
    except Exception as e:
        print(f"単一要約生成エラー: {str(e)}")
        raise


def generate_summary_chunked(text, prompt, config, ai_model, chunk_size):
    """分割テキストの要約生成"""
    try:
        chunks = split_text_smart(text, chunk_size)
        print(f"[DEBUG] テキストを{len(chunks)}個のチャンクに分割しました (モデル={ai_model})")
        
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            print(f"[DEBUG] チャンク {i+1}/{len(chunks)} 要約開始: 長さ={len(chunk)}")
            chunk_prompt = f"{prompt}\n\n以下は配信の一部です。この部分を要約してください：\n\n{chunk}"
            
            if ai_model == "openai-gpt4o":
                print("[DEBUG] OpenAI GPT-4o APIを呼び出します")
                summary = call_openai_api(chunk_prompt, config)
            elif ai_model == "google-gemini-2.5-flash":
                print("[DEBUG] Google Gemini 2.5 Flash APIを呼び出します")
                summary = call_google_api(chunk_prompt, config)
            else:
                raise Exception(f"未対応のAIモデル: {ai_model}")
            
            chunk_summaries.append(summary)
        
        print("[DEBUG] チャンク要約を統合して最終要約を生成します")
        combined_summaries = "\n\n".join(chunk_summaries)
        final_prompt = f"以下は配信の各部分の要約です。これらを統合して、配信全体の包括的な要約を作成してください：\n\n{combined_summaries}"
        
        if ai_model == "openai-gpt4o":
            print("[DEBUG] OpenAI GPT-4o APIを呼び出します（統合要約）")
            final_summary = call_openai_api(final_prompt, config)
        elif ai_model == "google-gemini-2.5-flash":
            print("[DEBUG] Google Gemini 2.5 Flash APIを呼び出します（統合要約）")
            final_summary = call_google_api(final_prompt, config)
        else:
            raise Exception(f"未対応のAIモデル: {ai_model}")
        
        print("[DEBUG] チャンク要約統合完了")
        return final_summary
        
    except Exception as e:
        print(f"分割要約生成エラー: {str(e)}")
        raise


def split_text_smart(text, chunk_size):
    """テキストを適切に分割（文の境界を考慮）"""
    chunks = []
    current_chunk = ""
    
    # 改行で分割
    lines = text.split('\n')
    
    for line in lines:
        # 現在のチャンクに追加した場合のサイズをチェック
        potential_chunk = current_chunk + '\n' + line if current_chunk else line
        
        if len(potential_chunk) <= chunk_size:
            current_chunk = potential_chunk
        else:
            # チャンクサイズを超える場合
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                # 単一行がチャンクサイズを超える場合、強制分割
                while len(line) > chunk_size:
                    chunks.append(line[:chunk_size])
                    line = line[chunk_size:]
                current_chunk = line
    
    # 最後のチャンクを追加
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def call_openai_api(prompt, config):
    """OpenAI GPT-4oを呼び出し"""
    try:
        api_key = config["api_settings"]["openai_api_key"]
        if not api_key:
            raise Exception("OpenAI API Keyが設定されていません")
        
        # デバッグログ
        print(f"[DEBUG] OpenAI API呼び出し開始: モデル=gpt-4o, prompt文字数={len(prompt)}")

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )

        # レスポンス情報をログ出力
        if hasattr(response, "usage"):
            print(f"[DEBUG] OpenAI使用トークン: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")
        else:
            print("[DEBUG] OpenAIトークン使用量情報なし")

        # 応答本文の取り出し
        result_text = response.choices[0].message.content.strip() if response.choices else ""
        if not result_text:
            print("[WARN] OpenAI APIから空のレスポンスが返されました")
        else:
            print(f"[DEBUG] OpenAIレスポンス文字数: {len(result_text)}")
        
        return result_text

    except Exception as e:
        print(f"OpenAI API呼び出しエラー: {str(e)}")
        raise


def call_google_api(prompt, config):
    """Google Gemini 2.5 Flashを呼び出し"""
    try:
        api_key = config["api_settings"]["google_api_key"]
        if not api_key:
            raise Exception("Google API Keyが設定されていません")
        
        # デバッグログ
        print(f"[DEBUG] Google API呼び出し開始: モデル=gemini-2.0-flash-exp, prompt文字数={len(prompt)}")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.7
            )
        )

        # 追加デバッグログ
        if hasattr(response, "candidates"):
            print(f"[DEBUG] Google APIレスポンス候補数: {len(response.candidates)}")
        if hasattr(response, "usage_metadata"):
            print(f"[DEBUG] Google API token使用量: {response.usage_metadata}")

        # 安全に text を取り出す
        result_text = getattr(response, "text", "").strip()
        if not result_text:
            print("[WARN] Google APIから空のレスポンスが返されました")
        else:
            print(f"[DEBUG] Google APIレスポンス文字数: {len(result_text)}")
        
        return result_text

    except Exception as e:
        print(f"Google API呼び出しエラー: {str(e)}")
        raise


def update_broadcast_json(broadcast_dir, lv_value, summary):
    """統合JSONに要約を追加"""
    try:
        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                broadcast_data = json.load(f)
            
            # 要約を追加
            broadcast_data['summary_text'] = summary
            broadcast_data['summary_generated_at'] = datetime.now().isoformat()
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
            
            print(f"統合JSONに要約を追加: {json_path}")
        else:
            print(f"統合JSONが見つかりません: {json_path}")
            
    except Exception as e:
        print(f"統合JSON更新エラー: {str(e)}")

def save_summary_text(broadcast_dir, lv_value, summary):
    """要約テキストファイルを保存"""
    try:
        summary_path = os.path.join(broadcast_dir, f"{lv_value}_summary.txt")
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"要約テキストファイル保存: {summary_path}")
        
    except Exception as e:
        print(f"要約テキストファイル保存エラー: {str(e)}")