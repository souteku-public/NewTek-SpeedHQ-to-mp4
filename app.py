import asyncio
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="SpeedHQ to MP4 Converter")
app.mount("/static", StaticFiles(directory="static"), name="static")

jobs: dict = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


@app.post("/api/convert")
async def convert(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "ファイルが指定されていません")

    job_id = str(uuid.uuid4())
    stem = Path(file.filename).stem
    input_path = UPLOAD_DIR / f"{job_id}{Path(file.filename).suffix}"
    output_path = OUTPUT_DIR / f"{job_id}.mp4"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    jobs[job_id] = {
        "status": "converting",
        "original_name": stem,
        "output_path": str(output_path),
        "progress": 0,
    }

    asyncio.create_task(run_conversion(job_id, input_path, output_path))
    return {"job_id": job_id}


async def get_duration(path: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0


def parse_time(line: str) -> float:
    """ffmpeg stderr 'time=HH:MM:SS.ss' を秒数に変換"""
    for part in line.split():
        if part.startswith("time="):
            t = part[5:]
            try:
                h, m, s = t.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
            except (ValueError, AttributeError):
                pass
    return 0.0


async def run_conversion(job_id: str, input_path: Path, output_path: Path):
    duration = await get_duration(input_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        stderr_buf = []
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            decoded = line.decode(errors="replace")
            stderr_buf.append(decoded)
            if duration > 0:
                elapsed = parse_time(decoded)
                if elapsed > 0:
                    jobs[job_id]["progress"] = min(int(elapsed / duration * 100), 99)

        await proc.wait()

        if proc.returncode == 0:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["progress"] = 100
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "".join(stderr_buf[-20:])
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
    finally:
        input_path.unlink(missing_ok=True)


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "ジョブが見つかりません")
    result = {"status": job["status"], "progress": job.get("progress", 0)}
    if job["status"] == "error":
        result["error"] = job.get("error", "不明なエラー")
    return result


@app.get("/api/download/{job_id}")
async def download(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "ファイルの準備ができていません")
    output_path = Path(job["output_path"])
    if not output_path.exists():
        raise HTTPException(404, "ファイルが見つかりません")
    filename = job["original_name"] + ".mp4"
    return FileResponse(
        str(output_path),
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
