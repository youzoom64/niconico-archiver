import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step03: 感情分析"""
    try:
        lv_value = pipeline_data['lv_value']
        
        print(f"Step03 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索（utils.pyの関数を使用）
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. transcript.json読み込み
        transcript_path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
        if not os.path.exists(transcript_path):
            raise Exception(f"transcript.jsonが見つかりません: {transcript_path}")
        
        # 3. 感情分析モデル初期化
        sentiment_analyzer = load_sentiment_model()
        
        # 4. 感情分析実行
        stats = analyze_and_update_transcript(transcript_path, sentiment_analyzer)
        
        # 5. 統合JSONに統計情報を追加
        update_broadcast_json(broadcast_dir, lv_value, stats)
        
        print(f"Step03 完了: {lv_value}")
        return {"updated_transcript": transcript_path, "sentiment_stats": stats}
        
    except Exception as e:
        print(f"Step03 エラー: {str(e)}")
        raise

def load_sentiment_model():
    """感情分析モデルを読み込み"""
    try:
        print("感情分析モデル読み込み中...")
        tokenizer = AutoTokenizer.from_pretrained(
            "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
        )
        model = AutoModelForSequenceClassification.from_pretrained(
            "lxyuan/distilbert-base-multilingual-cased-sentiments-student"
        )
        
        return SentimentAnalysis(model, tokenizer)
        
    except Exception as e:
        print(f"モデル読み込みエラー: {str(e)}")
        raise

def analyze_and_update_transcript(transcript_path, sentiment_analyzer):
    """transcript.jsonを読み込み、感情分析してスコアを更新"""
    try:
        # JSONファイル読み込み
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcripts = transcript_data.get('transcripts', [])
        print(f"感情分析対象: {len(transcripts)}セグメント")
        
        # 各セグメントの感情分析
        for i, segment in enumerate(transcripts):
            text = segment.get('text', '')
            if text.strip():
                # 感情分析実行
                sentiment_scores = sentiment_analyzer.predict(text)
                
                # スコア更新 [center, positive, negative]の順
                segment['center_score'] = round(sentiment_scores[0], 3)
                segment['positive_score'] = round(sentiment_scores[1], 3)
                segment['negative_score'] = round(sentiment_scores[2], 3)
                
                if (i + 1) % 50 == 0:
                    print(f"  {i + 1}/{len(transcripts)} 処理完了")
        
        # 統計情報計算
        stats = calculate_sentiment_stats(transcripts)
        
        # 更新されたJSONを保存（統計情報は含めない）
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"感情分析完了: {transcript_path}")
        print(f"平均スコア - Center: {stats['avg_center']:.3f}, Positive: {stats['avg_positive']:.3f}, Negative: {stats['avg_negative']:.3f}")
        
        return stats
        
    except Exception as e:
        print(f"感情分析エラー: {str(e)}")
        raise

def calculate_sentiment_stats(transcripts):
    """感情分析の統計情報を計算"""
    if not transcripts:
        return {
            'avg_center': 0.0,
            'avg_positive': 0.0,
            'avg_negative': 0.0,
            'max_center': 0.0,
            'max_positive': 0.0,
            'max_negative': 0.0,
            'max_center_time': 0,
            'max_positive_time': 0,
            'max_negative_time': 0,
            'total_segments': 0
        }
    
    center_scores = []
    positive_scores = []
    negative_scores = []
    
    max_center = 0.0
    max_positive = 0.0
    max_negative = 0.0
    max_center_time = 0
    max_positive_time = 0
    max_negative_time = 0
    
    for segment in transcripts:
        center = segment.get('center_score', 0.0)
        positive = segment.get('positive_score', 0.0)
        negative = segment.get('negative_score', 0.0)
        timestamp = segment.get('timestamp', 0)
        
        center_scores.append(center)
        positive_scores.append(positive)
        negative_scores.append(negative)
        
        # 最大値更新
        if center > max_center:
            max_center = center
            max_center_time = timestamp
        
        if positive > max_positive:
            max_positive = positive
            max_positive_time = timestamp
        
        if negative > max_negative:
            max_negative = negative
            max_negative_time = timestamp
    
    return {
        'avg_center': sum(center_scores) / len(center_scores),
        'avg_positive': sum(positive_scores) / len(positive_scores),
        'avg_negative': sum(negative_scores) / len(negative_scores),
        'max_center': max_center,
        'max_positive': max_positive,
        'max_negative': max_negative,
        'max_center_time': max_center_time,
        'max_positive_time': max_positive_time,
        'max_negative_time': max_negative_time,
        'total_segments': len(transcripts)
    }

def update_broadcast_json(broadcast_dir, lv_value, sentiment_stats):
    """統合JSONに感情分析統計を追加"""
    try:
        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                broadcast_data = json.load(f)
            
            # 感情分析統計を追加
            broadcast_data['sentiment_stats'] = sentiment_stats
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
            
            print(f"統合JSONに感情統計を追加: {json_path}")
        else:
            print(f"統合JSONが見つかりません: {json_path}")
            
    except Exception as e:
        print(f"統合JSON更新エラー: {str(e)}")

class SentimentAnalysis:
    def __init__(self, model, tokenizer):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model.to(self.device)
        self.model.eval()
        self.tokenizer = tokenizer

    def predict(self, text):
        try:
            # テキストが長すぎる場合は切り詰める
            if len(text) > 512:
                text = text[:512]
            
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = inputs.to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = F.softmax(outputs.logits, dim=1)
            
            # [center, positive, negative]の順で返す
            return probabilities[0].cpu().numpy().tolist()
            
        except Exception as e:
            print(f"感情分析予測エラー: {str(e)}")
            return [0.33, 0.33, 0.34]  # エラー時はデフォルト値