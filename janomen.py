import json
import sys
from collections import Counter
from janome.tokenizer import Tokenizer

def analyze_word_frequency(transcript_path):
    """Janomeを使用して単語の出現頻度を分析"""
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
    word_count = Counter()

    # 各セグメントのテキストを形態素解析
    for segment_text in text_segments:
        for token in tokenizer.tokenize(segment_text):
            pos = token.part_of_speech.split(",")[0]
            pos_detail1 = token.part_of_speech.split(",")[1]

            # 名詞の「一般」「固有名詞」のみを対象
            if pos == "名詞" and pos_detail1 in ["一般", "固有名詞", "サ変接続"]:
                surface = token.surface
                if surface and len(surface) > 1:
                    word_count[surface] += 1

    # 上位30位を取得
    top_words = word_count.most_common(30)

    # 辞書形式に変換
    word_ranking = []
    for i, (word, count) in enumerate(top_words, 1):
        word_ranking.append({
            "rank": i,
            "word": word,
            "count": count,
            "font_size": max(50 - i, 12)  # HTMLでのフォントサイズ用
        })

    print(f"単語頻度分析完了: 上位{len(word_ranking)}語")
    for item in word_ranking:
        print(f"{item['rank']}位: {item['word']} ({item['count']}回)")

    return word_ranking

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python step04_janome_test.py <transcript.json>")
        sys.exit(1)

    transcript_path = sys.argv[1]
    analyze_word_frequency(transcript_path)
