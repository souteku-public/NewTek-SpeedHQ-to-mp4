#!/usr/bin/env python3
"""SpeedHQ MOV → MP4 バッチ変換スクリプト

使い方:
  python3 batch.py /path/to/folder              # フォルダ内の全 MOV を変換
  python3 batch.py /path/to/folder -o /output   # 出力先を指定
  python3 batch.py /path/to/folder --watch      # 新ファイルを監視して自動変換
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


FFMPEG_CMD = [
    "-c:v", "libx264", "-crf", "18", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
]


def find_mov_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() == ".mov" and p.is_file())


def convert(src: Path, output_dir: Path | None) -> bool:
    dst_dir = output_dir or src.parent
    dst = dst_dir / (src.stem + ".mp4")

    if dst.exists():
        print(f"  スキップ（変換済み）: {dst.name}")
        return True

    cmd = ["ffmpeg", "-y", "-i", str(src)] + FFMPEG_CMD + [str(dst)]

    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )

    stderr_lines = []
    for line in proc.stderr:
        stderr_lines.append(line)
        # リアルタイム進捗表示（frame= / time= が含まれる行）
        if "frame=" in line or "time=" in line:
            print(f"\r  {line.rstrip()}", end="", flush=True)

    proc.wait()
    print()  # 改行

    if proc.returncode == 0:
        size_mb = dst.stat().st_size / 1024 / 1024
        print(f"  ✅ 完了: {dst.name}  ({size_mb:.1f} MB)")
        return True
    else:
        print(f"  ❌ 失敗: {src.name}")
        print("".join(stderr_lines[-15:]))
        if dst.exists():
            dst.unlink()
        return False


def batch_convert(folder: Path, output_dir: Path | None) -> None:
    files = find_mov_files(folder)
    if not files:
        print("MOV ファイルが見つかりません。")
        return

    total = len(files)
    print(f"\n{total} 件の MOV ファイルを変換します\n{'─' * 50}")
    ok = fail = 0

    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"\n[{i}/{total}] {f.name}  ({size_mb:.0f} MB)")
        if convert(f, output_dir):
            ok += 1
        else:
            fail += 1

    print(f"\n{'─' * 50}")
    print(f"完了  ✅ {ok} 件成功  ❌ {fail} 件失敗")


def watch_mode(folder: Path, output_dir: Path | None) -> None:
    print(f"フォルダ監視中: {folder}")
    print("新しい MOV ファイルを検出すると自動で変換します (Ctrl+C で停止)\n")

    seen: set[Path] = set()

    # 起動時に既存ファイルを "処理済み" として登録
    for f in find_mov_files(folder):
        mp4 = (output_dir or folder) / (f.stem + ".mp4")
        if mp4.exists():
            seen.add(f)
            print(f"  スキップ（変換済み）: {f.name}")

    print("\n待機中...\n")

    try:
        while True:
            for f in find_mov_files(folder):
                if f not in seen:
                    # ファイルが書き込み中でないか確認（サイズが安定するまで待つ）
                    if _is_stable(f):
                        seen.add(f)
                        size_mb = f.stat().st_size / 1024 / 1024
                        print(f"新ファイル検出: {f.name}  ({size_mb:.0f} MB)")
                        convert(f, output_dir)
                        print("\n待機中...\n")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n監視を終了しました。")


def _is_stable(path: Path, wait: float = 2.0) -> bool:
    """ファイルサイズが変化しなくなったら安定と判断"""
    size1 = path.stat().st_size
    time.sleep(wait)
    size2 = path.stat().st_size
    return size1 == size2 and size1 > 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SpeedHQ MOV → MP4 バッチ変換",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("folder", help="変換対象のフォルダパス")
    parser.add_argument("-o", "--output", metavar="DIR",
                        help="MP4 の出力先フォルダ（省略時は元フォルダと同じ）")
    parser.add_argument("--watch", action="store_true",
                        help="フォルダを監視して新しいファイルを自動変換")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"ERROR: フォルダが見つかりません: {folder}")
        sys.exit(1)

    output_dir = None
    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    if args.watch:
        watch_mode(folder, output_dir)
    else:
        batch_convert(folder, output_dir)


if __name__ == "__main__":
    main()
