# SpeedHQ → MP4 コンバーター

NDI 録画の MOV ファイル（NewTek SpeedHQ コーデック）を H.264 MP4 に変換する Web アプリです。
Premiere Pro で読み込めない SpeedHQ ファイルをブラウザから手軽に変換できます。

## 変換設定

| 項目 | 設定 |
|------|------|
| 映像コーデック | H.264 (CRF 18 / medium) |
| 音声コーデック | AAC 192kbps |
| 最適化 | Web 再生向け (`+faststart`) |

---

## ローカルで起動する

### 必要なもの
- Python 3.9 以上
- ffmpeg（インストールスクリプトが自動対応）

### セットアップ

```bash
git clone <このリポジトリ>
cd NewTek-SpeedHQ-to-mp4

# セットアップ（ffmpeg + Python パッケージ）
bash install.sh

# 起動
bash start.sh
```

ブラウザで `http://localhost:8000` にアクセスしてください。

### 手動セットアップ

```bash
# ffmpeg インストール
# macOS:  brew install ffmpeg
# Ubuntu: sudo apt-get install ffmpeg

pip install -r requirements.txt
python app.py
```

---

## Docker で起動する

```bash
docker build -t speedhq-converter .
docker run -p 8000:8000 speedhq-converter
```

---

## クラウドにデプロイする（リンクでアクセス）

### Render（無料枠あり・推奨）

1. [render.com](https://render.com) でアカウント作成
2. New → Web Service → このリポジトリを選択
3. 設定:
   - **Runtime**: Docker
   - **Port**: 8000
4. Deploy → 発行された URL でアクセス可能

### Railway

```bash
# Railway CLI 使用
railway login
railway init
railway up
```

### ngrok（一時的な公開）

```bash
# ローカルサーバーを起動しつつ、外部に公開
bash start.sh &
ngrok http 8000
# 表示された https://xxxx.ngrok.io でアクセス可能
```

---

## 注意事項

- 変換済みファイルはサーバー再起動でリセットされます（`outputs/` フォルダ）
- クラウドデプロイ時は永続ストレージ（S3 など）の追加を推奨します
- 大容量ファイル（数 GB）にも対応していますが、変換時間はファイルサイズに比例します
