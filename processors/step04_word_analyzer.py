import json
import os
import collections
from janome.tokenizer import Tokenizer
import sys

# utils.pyからfind_account_directoryをインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step04: 単語頻度分析"""
    try:
        lv_value = pipeline_data['lv_value']
        
        print(f"Step04 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. transcript.json読み込み
        transcript_path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
        if not os.path.exists(transcript_path):
            raise Exception(f"transcript.jsonが見つかりません: {transcript_path}")
        
        # 3. 単語頻度分析実行
        word_ranking = analyze_word_frequency(transcript_path)
        
        # 4. 統合JSONに結果を追加
        update_broadcast_json(broadcast_dir, lv_value, word_ranking)
        
        print(f"Step04 完了: {lv_value} - 分析単語数: {len(word_ranking)}")
        return {"word_ranking_count": len(word_ranking)}
        
    except Exception as e:
        print(f"Step04 エラー: {str(e)}")
        raise

def analyze_word_frequency(transcript_path):
    """Janomeを使用して単語の出現頻度を分析"""
    try:
        # transcript.jsonから文字起こしテキストを取得
        with open(transcript_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            transcripts = data.get("transcripts", [])
            text_segments = [segment["text"] for segment in transcripts if segment.get("text")]
        
        if not text_segments:
            print("分析対象のテキストが見つかりません")
            return []
        
        print(f"分析対象セグメント数: {len(text_segments)}")
        
        tokenizer = Tokenizer()
        word_count = collections.Counter()
        
        for segment_text in text_segments:
            for token in tokenizer.tokenize(segment_text):
                pos = token.part_of_speech.split(",")[0]  # 品詞
                pos_detail = token.part_of_speech.split(",")[1]  # 品詞細分類1
                
                # 名詞の「一般」「固有名詞」「サ変接続」を対象
                if pos == "名詞" and pos_detail in ["一般", "固有名詞", "サ変接続"]:
                    surface = token.surface
                    if surface and len(surface) > 1:  # 1文字は除外
                        word_count[surface] += 1
        
        top_words = word_count.most_common(30)
        
        word_ranking = []
        for i, (word, count) in enumerate(top_words, 1):
            word_ranking.append({
                "rank": i,
                "word": word,
                "count": count,
                "font_size": max(50 - i, 12)
            })
        
        print(f"単語頻度分析完了: 上位{len(word_ranking)}語")
        for item in word_ranking[:5]:
            print(f"  {item['rank']}位: {item['word']} ({item['count']}回)")
        
        return word_ranking
        
    except Exception as e:
        print(f"単語頻度分析エラー: {str(e)}")
        raise

def update_broadcast_json(broadcast_dir, lv_value, word_ranking):
    """統合JSONに単語ランキングを追加"""
    try:
        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                broadcast_data = json.load(f)
            
            broadcast_data['word_ranking'] = word_ranking
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
            
            print(f"統合JSONに単語ランキングを追加: {json_path}")
        else:
            print(f"統合JSONが見つかりません: {json_path}")
            
    except Exception as e:
        print(f"統合JSON更新エラー: {str(e)}")
