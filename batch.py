#!/usr/bin/env python3
"""SpeedHQ MOV → MP4 バッチ変換スクリプト

使い方:
  python3 batch.py /path/to/folder                     # 標準変換
  python3 batch.py /path/to/folder --preset veryfast   # CPU高速モード（約3倍速）
  python3 batch.py /path/to/folder --hw                # GPU高速モード（最速・Mac推奨）
  python3 batch.py /path/to/folder -o /output          # 出力先を指定
  python3 batch.py /path/to/folder --watch             # 新ファイルを監視して自動変換
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def build_ffmpeg_cmd(src: Path, dst: Path, preset: str, hw: bool) -> list[str]:
    if hw:
        # Mac の GPU ハードウェアエンコーダー（VideoToolbox）
        return [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "h264_videotoolbox",
            "-q:v", "60",          # 品質: 1（低）〜 100（高）、60 が高品質
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(dst),
        ]
    else:
        return [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264", "-crf", "18", "-preset", preset,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(dst),
        ]


def find_mov_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() == ".mov" and p.is_file())


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def parse_time(line: str) -> float:
    for part in line.split():
        if part.startswith("time="):
            t = part[5:]
            try:
                h, m, s = t.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            except (ValueError, AttributeError):
                pass
    return 0.0


def fmt_time(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def progress_bar(pct: int, width: int = 28) -> str:
    filled = int(width * pct / 100)
    return f"[{'█' * filled}{'░' * (width - filled)}] {pct:3d}%"


def convert(src: Path, output_dir: Path | None, preset: str, hw: bool) -> bool:
    dst_dir = output_dir or src.parent
    dst = dst_dir / (src.stem + ".mp4")

    if dst.exists():
        print(f"  スキップ（変換済み）: {dst.name}")
        return True

    duration = get_duration(src)
    cmd = build_ffmpeg_cmd(src, dst, preset, hw)

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
        if "time=" not in line:
            continue
        elapsed = parse_time(line)
        if elapsed <= 0:
            continue

        speed = next((p for p in line.split() if p.startswith("speed=")), "")

        if duration > 0:
            pct = min(int(elapsed / duration * 100), 99)
            remaining = (duration - elapsed) / float(speed[6:-1]) if speed and speed[6:-1] not in ("N/A", "") else 0
            bar = progress_bar(pct)
            time_str = f"{fmt_time(elapsed)} / {fmt_time(duration)}"
            eta = f"  残り約 {fmt_time(remaining)}" if remaining > 0 else ""
            print(f"\r  {bar}  {time_str}  {speed}{eta}   ", end="", flush=True)
        else:
            print(f"\r  変換中: {fmt_time(elapsed)}  {speed}   ", end="", flush=True)

    proc.wait()
    print()

    if proc.returncode == 0:
        size_mb = dst.stat().st_size / 1024 / 1024
        print(f"  ✅ 完了: {dst.name}  ({size_mb:.1f} MB)")
        return True
    else:
        # ハードウェアエンコードに失敗した場合はソフトウェアにフォールバック
        if hw:
            print("  ⚠️  GPU エンコードに失敗。ソフトウェアで再試行します...")
            return convert(src, output_dir, preset, hw=False)
        print(f"  ❌ 失敗: {src.name}")
        print("".join(stderr_lines[-15:]))
        if dst.exists():
            dst.unlink()
        return False


def batch_convert(folder: Path, output_dir: Path | None, preset: str, hw: bool) -> None:
    files = find_mov_files(folder)
    if not files:
        print("MOV ファイルが見つかりません。")
        return

    mode = "GPU ハードウェア (VideoToolbox)" if hw else f"CPU ソフトウェア (preset={preset})"
    total = len(files)
    print(f"\n{total} 件の MOV ファイルを変換します  [{mode}]\n{'─' * 55}")
    ok = fail = 0
    start_all = time.time()

    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"\n[{i}/{total}] {f.name}  ({size_mb:.0f} MB)")
        t0 = time.time()
        if convert(f, output_dir, preset, hw):
            ok += 1
            elapsed = time.time() - t0
            print(f"  所要時間: {fmt_time(elapsed)}")
        else:
            fail += 1

    total_elapsed = time.time() - start_all
    print(f"\n{'─' * 55}")
    print(f"完了  ✅ {ok} 件成功  ❌ {fail} 件失敗  合計時間: {fmt_time(total_elapsed)}")


def watch_mode(folder: Path, output_dir: Path | None, preset: str, hw: bool) -> None:
    mode = "GPU ハードウェア (VideoToolbox)" if hw else f"CPU ソフトウェア (preset={preset})"
    print(f"フォルダ監視中: {folder}  [{mode}]")
    print("新しい MOV ファイルを検出すると自動で変換します (Ctrl+C で停止)\n")

    seen: set[Path] = set()

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
                    if _is_stable(f):
                        seen.add(f)
                        size_mb = f.stat().st_size / 1024 / 1024
                        print(f"新ファイル検出: {f.name}  ({size_mb:.0f} MB)")
                        convert(f, output_dir, preset, hw)
                        print("\n待機中...\n")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n監視を終了しました。")


def _is_stable(path: Path, wait: float = 2.0) -> bool:
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
    parser.add_argument("--preset",
                        choices=["ultrafast", "superfast", "veryfast",
                                 "faster", "fast", "medium", "slow"],
                        default="medium",
                        help="エンコード速度 (default: medium)。速さ優先なら veryfast")
    parser.add_argument("--hw", action="store_true",
                        help="GPU ハードウェアエンコードを使用（Mac 推奨・最速）")
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
        watch_mode(folder, output_dir, args.preset, args.hw)
    else:
        batch_convert(folder, output_dir, args.preset, args.hw)


if __name__ == "__main__":
    main()
