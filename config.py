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

    REPLACE_WORDS: List[tuple] = [("cleo", "clio"), ("FaZe", "Phase"), ("&gt;&gt;", "")]

    # Time slicing parameters
    START_TIME_SEC: Optional[int] = None  # Start time in seconds (None = video start)
    END_TIME_SEC: Optional[int] = None  # End time in seconds (None = video end)

    # Analysis reporting
    GENERATE_ANALYSIS_REPORT: bool = True
    INCLUDE_TRANSCRIPT_CONTEXT: bool = True
    REPORT_FORMAT: str = "html"  # Options: html, json, txt, all
    REPORT_INCLUDE_RAW_DATA: bool = False  # Exclude full datasets by default
    REPORT_COMPRESS_JSON: bool = True  # Use gzip for large JSON files
    REPORT_TEMPLATE: str = "modern"  # Template style: modern, compact, detailed
    HTML_INCLUDE_CHARTS: bool = True  # Generate interactive charts
    MAX_TRANSCRIPT_EXCERPT: int = 500  # Limit transcript characters per highlight


# Usage example for main.py
def get_config(url, start_time=None, end_time=None):
    video_id = url.split("v=")[-1].split("&")[0]
    return AppConfig(
        YOUTUBE_URL=url,
        OUTPUT_DIR=f"./data/{video_id}",
        START_TIME_SEC=start_time,
        END_TIME_SEC=end_time,
    )
