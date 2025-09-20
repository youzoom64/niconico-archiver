# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

ニコニコ生放送の録画ファイルを自動監視し、AI技術を使って包括的なアーカイブページを生成するPythonベースのシステムです。音声の文字起こし、感情分析、AI要約、画像生成、音楽生成、インタラクティブなHTMLアーカイブ生成を提供します。

## 開発用コマンド

### アプリケーション実行
```bash
# メインGUIアプリケーション起動
python main.py

# 特定配信のパイプライン処理テスト
python pipeline.py niconico [account_id] [platform_dir] [ncv_dir] [lv_id]

# 自動録画開始（Chrome拡張機能が必要）
python auto_recorder.py -url [配信URL] -tag [lv12345_タイトル_配信者_ID]
```

### 依存関係管理
```bash
# 必要な依存関係をインストール
pip install -r requirements.txt

# 主要依存関係: torch, faster-whisper, openai, google-generativeai, moviepy, watchdog
```

### テスト
```bash
# 録画システムテスト
python test_rec.py -url [url] -tag [tag]
```

## システム構成

### コアコンポーネント

**メインアプリケーション (`main.py`)**
- 複数ユーザーアカウント管理用Tkinter GUI
- リアルタイム監視状況とシステム情報表示
- ユーザー設定管理インターフェース
- GPU利用可能性検出と表示

**ファイル監視 (`file_monitor.py`)**
- watchdogを使用したマルチユーザーファイルシステム監視
- lv[番号]パターンの新規MP4ファイル自動検出
- 処理前のファイル安定性チェック
- 処理パイプラインとの連携

**処理パイプライン (`pipeline.py`)**
- 13ステップのモジュラー処理システム
- ユーザー設定に基づく条件付き実行
- プロセッサーステップの動的モジュール読み込み
- パイプライン継続型エラーハンドリング

**設定システム (`config_manager.py`)**
- JSONベースのユーザー設定保存
- 複数アカウント管理サポート
- APIキー管理と機能切り替え

### 処理パイプライン ステップ

1. **step01_data_collector** - 基本放送情報抽出と初期JSON作成
2. **step02_audio_transcriber** - GPU加速対応Whisper音声文字起こし
3. **step03_emotion_scorer** - 文字起こし内容の感情分析
4. **step04_word_analyzer** - 頻度分析とキーワード抽出
5. **step05_summarizer** - AI要約生成（GPT/Gemini）
6. **step06_music_generator** - Suno API音楽生成連携
7. **step07_image_generator** - DALL-E 3配信視覚化画像生成
8. **step08_conversation_generator** - AIキャラクター対話生成
9. **step09_screenshot_generator** - サムネイルとスクリーンショット生成
10. **step10_comment_processor** - ユーザーコメント分析とランキング
11. **step11_special_user_html_generator** - 特定ユーザー詳細ページ
12. **step12_html_generator** - メインアーカイブページ生成
13. **step13_index_generator** - インデックスとタグベースナビゲーション

### 設定構造

ユーザー設定は `config/users/[account_id].json` に以下のセクションで保存：

- **basic_settings**: プラットフォーム、アカウントID、ディレクトリパス
- **ai_features**: AI機能切り替え（要約、画像、音楽、会話）
- **display_features**: 表示要素制御（感情スコア、ランキング、サムネイル）
- **api_settings**: OpenAI、Google、Suno、Imgur用APIキー
- **audio_settings**: GPU使用、Whisperモデル選択、処理パラメータ
- **special_users**: 特定ユーザーの詳細分析
- **ai_conversation**: 対話生成用キャラクター設定

## 重要な開発パターン

### モジュール読み込みパターン
パイプラインは条件付き処理を可能にする動的モジュール読み込みを使用：
```python
module = importlib.import_module(f"processors.{step_name}")
result = module.process(pipeline_data)
```

### 設定駆動型処理
各処理ステップはユーザー設定をチェックして実行可否を判定：
```python
def should_run_step(config, step_name):
    step_mapping = {
        'step02_audio_transcriber': config['ai_features']['enable_summary_text'],
        # ... その他のマッピング
    }
    return step_mapping.get(step_name, True)
```

### ファイルシステム監視
安定性チェック付きのwatchdogリアルタイムファイル監視：
```python
# ファイル書き込み完了確認のため5秒遅延
self.stability_threads[filename] = threading.Timer(5.0, self.check_file_stability, [filename])
```

## テンプレートシステム

HTML生成はテンプレートベースアプローチを使用：
- **templates/archive.html** - メイン放送アーカイブテンプレート
- **templates/user_list.html** - ユーザー一覧テンプレート
- **templates/user_detail.html** - ユーザー詳細分析テンプレート
- **templates/css/** - パーティクルエフェクトとレスポンシブデザイン
- **templates/js/** - インタラクティブ機能と音声プレーヤー制御

## 出力構造

### 放送別ディレクトリ (`rec/[account_id]/[lv_id]/`)
```
lv123456_data.json              # 統合放送データ
lv123456_transcript.json        # 音声文字起こし結果
lv123456_comments.json          # コメントデータと分析
lv123456_summary.txt            # AI生成要約
lv123456_full_audio.mp3         # 抽出音声
lv123456_[タイトル].html        # メインアーカイブページ
screenshot/lv123456/           # 生成サムネイル
```

### アカウントルート (`rec/[account_id]/`)
```
index.html                     # 放送一覧ページ
tags/tag_[名前].html          # タグベースナビゲーション
special_user_[id]/            # ユーザー詳細分析ページ
```

## 重要な実装ノート

### GPU加速
- システムはCUDA利用可能性を自動検出
- Whisper文字起こしはGPUで大幅な速度向上
- 設定可能スレッド数でCPU処理にフォールバック

### API連携要件
- **OpenAI API** - GPT-4o要約とDALL-E 3画像生成に必須
- **Google API** - Gemini 2.5 Flash会話に必須
- **Suno API** - AI音楽生成にオプション
- **Imgur API** - 画像ホスティングにオプション

### ファイル命名規則
- 放送ファイルは検出のため `lv[番号]` パターン必須
- アカウントディレクトリは `[account_id]_[表示名]` 形式
- 生成ファイルは `[lv_id]_[記述子].[拡張子]` パターン

### エラーハンドリング戦略
- 個別ステップが失敗してもパイプライン処理継続
- `logs/` ディレクトリへの包括的ログ記録
- GUIインターフェースでのユーザーフレンドリーなエラー表示
- API呼び出しの自動リトライ機構

### マルチユーザーサポート
- 各ユーザーアカウントに独立した設定
- 複数ディレクトリの同時監視
- アカウント固有の機能切り替えとAPI設定
- ユーザー毎の分離された処理パイプライン