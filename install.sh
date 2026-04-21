#!/bin/bash
set -e

echo "=== SpeedHQ → MP4 コンバーター セットアップ ==="

# ffmpeg のインストール確認
if ! command -v ffmpeg &> /dev/null; then
  echo ">>> ffmpeg をインストール中..."
  if command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y ffmpeg
  elif command -v brew &> /dev/null; then
    brew install ffmpeg
  else
    echo "ERROR: ffmpeg が見つかりません。手動でインストールしてください。"
    echo "  macOS:  brew install ffmpeg"
    echo "  Ubuntu: sudo apt-get install ffmpeg"
    exit 1
  fi
else
  echo ">>> ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
fi

# Python 依存関係のインストール
echo ">>> Python パッケージをインストール中..."
python3 -m pip install -r requirements.txt

mkdir -p uploads outputs

echo ""
echo "✅ セットアップ完了！"
echo "   起動: bash start.sh  または  python app.py"
echo "   アクセス: http://localhost:8000"
