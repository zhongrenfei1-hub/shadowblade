"""Stock footage acquisition — fetch real video clips for the mix pipeline.

Two sources:

  - ``pexels``    free, royalty-free, commercially safe. Needs a ``PEXELS_API_KEY``
    (get one in 1 minute at https://www.pexels.com/api/). Best for "topic →
    auto-find clips" flows because the API takes a keyword and returns ranked
    videos.

  - ``ytdlp``     yt-dlp — universal URL downloader. Works on YouTube,
    Bilibili, Vimeo, TikTok, Douyin, Twitter, and ~1500 other sites. No key.
    Use for "I have a specific URL and want a 10-second clip from 0:20–0:30".

Both write to ``<storage_root>/stock/<source>/<id>.mp4`` and return absolute
paths the mix pipeline can ingest unchanged.
"""

from app.services.stock.pexels import PexelsClip, pexels_download, pexels_search
from app.services.stock.youtube import YtClip, has_ytdlp, ytdlp_download

__all__ = [
    "PexelsClip",
    "pexels_search",
    "pexels_download",
    "YtClip",
    "has_ytdlp",
    "ytdlp_download",
]
