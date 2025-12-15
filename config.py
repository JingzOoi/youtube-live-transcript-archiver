YOUTUBE_CHANNEL_ID = ""
MAX_VIDEO_LOOKBACK = 200
YTDLP_EXECUTABLE = "/home/jz/sides/youtube-live-transcript-archiver/.venv/bin/yt-dlp"
TWITCHDOWNLOADER_EXECUTABLE = "/usr/bin/TwitchDownloaderCLI"

from pydantic import BaseModel
from typing import Tuple, Optional, List


class AppConfig(BaseModel):
    YOUTUBE_URL: str
    OUTPUT_DIR: str = "./data"

    DRY_RUN: bool = False  # Set to True for testing
    VERBOSE: bool = True  # Detailed logging

    # Analysis
    ROLLING_WINDOW_MIN: int = 20
    SPIKE_Z_SCORE_THRESHOLD: float = 3.0
    PADDING_PRE_SEC: int = 120
    PADDING_POST_SEC: int = 60

    # Error handling configuration
    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds
    TIMEOUT: int = 300  # seconds for network operations

    # Validation thresholds
    MIN_CHAT_MESSAGES: int = 10  # Minimum messages to consider analysis valid
    MAX_FILE_SIZE_MB: int = 5000  # Maximum file size to process

    # Keywords
    KEYWORDS: List[str] = [
        "lmao",
        "lol",
        "wow",
        "gg",
        "kekw",
        "wtf",
        "fuck",
        "clioaiKEKW",
    ]


# Usage example for main.py
def get_config(url):
    video_id = url.split("v=")[-1].split("&")[0]
    return AppConfig(YOUTUBE_URL=url, OUTPUT_DIR=f"./data/{video_id}")
