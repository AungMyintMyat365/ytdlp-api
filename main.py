from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp, asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
executor = ThreadPoolExecutor(max_workers=4)

class VideoRequest(BaseModel):
    url: str
    quality: str = "1080p"

QUALITY_MAP = {
    "2160p": "bestvideo[height>=2160]+bestaudio/best[height>=2160]/bestvideo[height>=1440]+bestaudio/best[height>=1440]/best",
    "1440p": "bestvideo[height>=1440]+bestaudio/best[height>=1440]/bestvideo[height>=1080]+bestaudio/best[height>=1080]/best",
    "1080p": "bestvideo[height>=1080]+bestaudio/best[height>=1080]/bestvideo[height>=720]+bestaudio/best[height>=720]/best",
    "720p": "bestvideo[height>=720]+bestaudio/best[height>=720]/bestvideo[height>=480]+bestaudio/best[height>=480]/best",
    "480p": "bestvideo[height>=480]+bestaudio/best[height>=480]/best",
    "360p": "bestvideo[height>=360]+bestaudio/best[height>=360]/best",
}

def extract_info(url: str, quality: str):
    fmt = QUALITY_MAP.get(quality, QUALITY_MAP["1080p"])
    ydl_opts = {'format': fmt, 'quiet': True, 'no_warnings': True, 'skip_download': True, 'merge_output_format': 'mp4'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        for f in info.get('formats', []):
            if f.get('url') and f.get('vcodec') != 'none':
                formats.append({'url': f.get('url'), 'height': f.get('height'), 'width': f.get('width'), 'ext': f.get('ext'), 'filesize': f.get('filesize'), 'tbr': f.get('tbr')})
        return {'id': info.get('id'), 'title': info.get('title'), 'thumbnail': info.get('thumbnail'), 'duration': info.get('duration'), 'uploader': info.get('uploader'), 'formats': formats}

@app.post("/api/json")
async def get_info(req: VideoRequest):
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(executor, extract_info, req.url, req.quality)
        target = int(req.quality.replace('p', ''))
        best = None
        for f in info['formats']:
            if f['height'] and f['height'] >= target:
                if not best or (f['height'] and f['height'] < best['height']): best = f
        if not best and info['formats']: best = max(info['formats'], key=lambda x: x['height'] or 0)
        return {"status": "success", "title": info['title'], "thumbnail": info['thumbnail'], "duration": info['duration'], "author": info['uploader'], "url": best['url'] if best else None, "quality": req.quality, "format": best['ext'] if best else 'mp4', "width": best.get('width'), "height": best.get('height'), "filesize": best.get('filesize')}
    except Exception as e: raise HTTPException(500, str(e))

@app.get("/health")
def health(): return {"status": "ok"}
