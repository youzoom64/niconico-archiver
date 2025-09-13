# ニコ生アーカイブ監視システム マニュアル

## 概要

ニコニコ生放送の録画ファイルを自動監視し、AI技術を使って包括的なアーカイブページを生成するシステムです。

## 主な機能

- **自動監視**: 新しい録画ファイルを検出して自動処理
- **音声処理**: Whisper AIによる高精度な音声文字起こし
- **感情分析**: 発言内容の感情スコア分析
- **AI要約**: GPT/Geminiによる配信内容の自動要約
- **AI会話生成**: キャラクター同士の配信振り返り会話
- **画像生成**: DALL-E 3による配信イメージ画像
- **音楽生成**: Suno APIによる要約歌詞の楽曲生成
- **コメント分析**: ユーザー別コメント統計とランキング
- **HTML生成**: 統合されたアーカイブページ作成

## 必要な環境

### システム要件
- Python 3.8以上
- Windows/Linux/macOS
- GPU推奨（CUDA対応、音声処理高速化）
- メモリ8GB以上推奨

### 必要なソフトウェア
- FFmpeg（音声・動画処理用）
- MeCab（日本語形態素解析用）

### 必要なAPIキー
- **OpenAI API Key** (GPT-4o, DALL-E 3用)
- **Google API Key** (Gemini 2.5 Flash用)
- **Suno API Key** (音楽生成用、オプション)
- **Imgur API Key** (画像アップロード用、オプション)

## インストール

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd nico-archive-system
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 3. MeCabのインストール
#### Windows
```bash
pip install mecab-python3
# MeCab本体とIPA辞書も別途インストールが必要
```

#### Linux/macOS
```bash
sudo apt-get install mecab mecab-ipadic-utf8  # Ubuntu/Debian
brew install mecab mecab-ipadic  # macOS
pip install mecab-python3
```

### 4. FFmpegのインストール
- [FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード
- PATHに追加

## セットアップ

### 1. 初回起動
```bash
python main.py
```

### 2. ユーザー設定の作成
1. **「ユーザー設定管理」**ボタンをクリック
2. **「新規作成」**をクリック
3. 以下の設定を入力：
   - **アカウントID**: ニコニコのユーザーID
   - **表示名**: 管理用の表示名
   - **監視Dir**: 録画ファイルが保存されるディレクトリ
   - **NCVDir**: ニコニココメントビューアーのログディレクトリ

### 3. API設定
1. **API設定**セクションで各APIキーを設定：
   - **OpenAI API Key**: GPT-4o、DALL-E 3用
   - **Google API Key**: Gemini 2.5 Flash用
   - **Suno API Key**: 音楽生成用（オプション）
   - **Imgur API Key**: 画像アップロード用（オプション）

2. **AIモデル選択**:
   - **要約AIモデル**: 配信要約用（GPT-4o推奨）
   - **会話AIモデル**: キャラクター会話用（Gemini推奨）

### 4. 音声処理設定
- **GPU使用**: 利用可能な場合にGPUを使用
- **Whisperモデル**: 精度と速度のバランス（large-v3推奨）
- **CPUスレッド数**: CPU処理時のスレッド数
- **ビームサイズ**: GPU処理時の精度設定

## 使用方法

### 基本的な使い方

1. **監視開始**
   - メイン画面でアカウントを選択
   - **「開始」**ボタンをクリック
   - 指定ディレクトリの監視が開始されます

2. **自動処理の流れ**
   ```
   録画ファイル検出 → 音声抽出 → 文字起こし → 感情分析 → 
   要約生成 → AI会話生成 → 画像生成 → 音楽生成 → HTML生成
   ```

3. **結果確認**
   - 各配信フォルダに処理結果が保存
   - `index.html`で配信一覧を確認
   - 個別HTMLで詳細なアーカイブを確認

### 詳細機能設定

#### AI会話キャラクター設定
```
キャラクター1: ニニちゃん（ボケ役、標準語）
キャラクター2: ココちゃん（ツッコミ役、関西弁）
```
- **名前**: キャラクター名
- **性格**: 話し方や性格の設定
- **画像URL**: キャラクター画像（オプション）
- **左右反転**: 画像の向きを調整
- **会話往復数**: 生成する会話の長さ

#### スペシャルユーザー設定
特定のユーザーに対して詳細分析ページを生成：

1. **テキスト入力**: カンマ区切りでユーザーIDを入力
2. **個別設定**: ユーザーごとの詳細設定
   - **AI分析**: 有効/無効
   - **AIモデル**: 分析用モデル選択
   - **分析プロンプト**: カスタム分析指示
   - **テンプレート**: 表示用テンプレート

#### タグ設定
配信内容に基づく自動タグ付け：
- カンマ区切りでタグを入力
- 配信タイトル・要約・文字起こしから自動マッチング
- タグ別一覧ページを自動生成

### 表示機能のカスタマイズ

#### 有効/無効を切り替え可能な機能
- **感情スコア表示**: 発言の感情分析結果
- **コメントランキング**: ユーザー別コメント統計
- **単語ランキング**: 頻出単語の分析
- **サムネイル表示**: 時系列スクリーンショット
- **音声プレイヤー**: 配信音声の再生機能
- **タイムシフトジャンプ**: ニコ生タイムシフトへのリンク

## ファイル構造

```
project/
├── main.py                     # メインアプリケーション
├── config_manager.py           # 設定管理
├── file_monitor.py            # ファイル監視
├── pipeline.py                # 処理パイプライン
├── user_config.py             # ユーザー設定UI
├── utils.py                   # ユーティリティ
├── config/                    # 設定ファイル
│   └── users/                 # ユーザー別設定
├── processors/                # 処理モジュール
│   ├── step01_data_collector.py      # データ収集
│   ├── step02_audio_transcriber.py   # 音声文字起こし
│   ├── step03_emotion_scorer.py      # 感情分析
│   ├── step04_word_analyzer.py       # 単語分析
│   ├── step05_summarizer.py          # 要約生成
│   ├── step06_music_generator.py     # 音楽生成
│   ├── step07_image_generator.py     # 画像生成
│   ├── step08_conversation_generator.py # 会話生成
│   ├── step09_screenshot_generator.py   # スクリーンショット
│   ├── step10_comment_processor.py      # コメント処理
│   ├── step11_special_user_html_generator.py # 特別ユーザーページ
│   ├── step12_html_generator.py             # メインHTML生成
│   └── step13_index_generator.py            # 一覧ページ生成
├── templates/                 # HTMLテンプレート
│   ├── css/                   # スタイルシート
│   └── js/                    # JavaScript
└── logs/                      # ログファイル
```

## 生成されるファイル

### 各配信フォルダ（例：`rec/12345_user/lv123456/`）
```
lv123456_data.json              # 統合データ
lv123456_transcript.json        # 文字起こし結果
lv123456_comments.json          # コメントデータ
lv123456_comment_ranking.json   # コメントランキング
lv123456_summary.txt            # 要約テキスト
lv123456_full_audio.mp3         # 抽出音声
lv123456_配信タイトル.html      # メインアーカイブページ
screenshot/                     # スクリーンショット
    └── lv123456/
        ├── 0.png
        ├── 10.png
        └── ...
```

### アカウントルート（例：`rec/12345_user/`）
```
index.html                      # 配信一覧ページ
tags/                          # タグ別ページ
    ├── tag_ゲーム.html
    └── tag_雑談.html
special_user_67890/            # スペシャルユーザー専用ページ
    ├── 67890_lv123456_detail.html
    └── 67890_list.html
```

## トラブルシューティング

### よくある問題

#### GPU関連
```bash
# CUDA確認
python -c "import torch; print(torch.cuda.is_available())"

# GPU使用無効化（CPU強制使用）
# 設定画面で「GPU使用」のチェックを外す
```

#### 音声処理エラー
```bash
# FFmpegインストール確認
ffmpeg -version

# 依存関係再インストール
pip install --upgrade torch torchaudio
pip install --upgrade faster-whisper
```

#### APIエラー
- **OpenAI**: API使用量・課金状況を確認
- **Google**: API有効化とクォータを確認
- **Suno/Imgur**: APIキーの有効性を確認

#### メモリ不足
- **Whisperモデル**: より軽量なモデル（medium, small）に変更
- **CPUスレッド数**: 値を下げる
- **GPU使用**: 無効化してCPU処理に変更

### ログの確認
```bash
# ログファイル確認
tail -f logs/watchdog.log

# デバッグ実行
python main.py
```

### 設定リセット
```bash
# 設定ディレクトリを削除（注意：全設定が削除されます）
rm -rf config/
```

## 高度な使用方法

### カスタムテンプレート
1. `templates/`ディレクトリに新しいHTMLテンプレートを作成
2. スペシャルユーザー設定でテンプレートファイル名を指定
3. 独自のレイアウトでユーザーページを生成

### プロンプトカスタマイズ
- **要約プロンプト**: より具体的な要約指示
- **分析プロンプト**: ユーザー分析の観点を変更
- **会話プロンプト**: キャラクターの会話スタイル調整

### バッチ処理
```bash
# 既存ファイルの一括処理
python pipeline.py niconico 12345 rec ncv lv123456
```

## 注意事項

### プライバシー・著作権
- 録画ファイルの取り扱いは配信者・プラットフォームの規約に従う
- 生成されたコンテンツの公開時は著作権に注意
- APIで生成されたコンテンツの利用規約を確認

### リソース使用量
- GPU使用時は大量のVRAMを消費
- 長時間配信の処理は時間がかかる場合がある
- API使用量・課金に注意

### データ保存
- 処理結果は大量のディスク容量を使用
- 定期的な不要ファイル削除を推奨
- 重要なデータのバックアップを推奨

## サポート・更新

### 機能要望・バグ報告
- GitHubのIssuesに報告
- ログファイルとエラー内容を添付

### アップデート
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### コミュニティ
- Discord/フォーラムでの情報交換
- 設定例・カスタマイズ例の共有