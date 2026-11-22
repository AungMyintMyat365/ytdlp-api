from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp, asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)

class VideoRequest(BaseModel):
    url: str
    quality: str = "1080p"

# More flexible format selectors with fallbacks
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
    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'merge_output_format': 'mp4',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        for f in info.get('formats', []):
            if f.get('url') and f.get('vcodec') != 'none':
                formats.append({
                    'url': f.get('url'),
                    'height': f.get('height'),
                    'width': f.get('width'),
                    'ext': f.get('ext'),
                    'filesize': f.get('filesize'),
                    'tbr': f.get('tbr'),
                    'format_id': f.get('format_id'),
                    'protocol': f.get('protocol'),
                })
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader'),
            'formats': formats,
            'requested_formats': info.get('requested_formats', []),
        }

@app.post("/api/json")
async def get_info(req: VideoRequest):
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(executor, extract_info, req.url, req.quality)
        
        # Find best format from all available
        target = int(req.quality.replace('p', ''))
        best = None
        
        # Check requested_formats first (merged formats)
        for f in info.get('requested_formats', []):
            if f.get('height') and f['height'] >= target:
                if not best or (f['height'] and f['height'] < best['height']):
                    best = f
        
        # Fallback to regular formats
        if not best:
            for f in info['formats']:
                if f['height'] and f['height'] >= target:
                    if not best or (f['height'] and f['height'] < best['height']):
                        best = f
        
        # Final fallback - highest available
        if not best and info['formats']:
            best = max(info['formats'], key=lambda x: x['height'] or 0)
        
        return {
            "status": "success",
            "title": info['title'],
            "thumbnail": info['thumbnail'],
            "duration": info['duration'],
            "author": info['uploader'],
            "url": best['url'] if best else None,
            "quality": req.quality,
            "format": best['ext'] if best else 'mp4',
            "width": best.get('width') if best else None,
            "height": best.get('height') if best else None,
            "filesize": best.get('filesize') if best else None,
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/formats")
async def list_formats(url: str):
    """Debug endpoint to list all available formats"""
    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "formats": [
                    {
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "resolution": f.get("resolution"),
                        "height": f.get("height"),
                        "width": f.get("width"),
                        "tbr": f.get("tbr"),
                        "vcodec": f.get("vcodec"),
                        "acodec": f.get("acodec"),
                        "protocol": f.get("protocol"),
                    }
                    for f in info.get("formats", [])
                    if f.get("vcodec") != "none"
                ]
            }
    except Exception as e:
        raise HTTPException(500, str(e))
