# YouTube Livestream Transcript & Chat Archiver

A Python tool to automatically download, parse, and archive transcripts and live chat replays from YouTube livestreams.

## Features

- **Automatic Monitoring**: Periodically checks a YouTube channel for new livestreams and processes them.
- **Data Download**: Fetches English auto-generated transcripts (VTT) and live chat replays (JSON) using `yt-dlp`.
- **Intelligent Parsing**:
    - **Transcripts**: Cleans and consolidates VTT caption data, removing artifacts and merging fragmented cues.
    - **Live Chat**: Parses JSON chat data, extracting messages, authors, timestamps, and SuperChat details.
- **Structured Storage**: Saves processed data in an efficient Parquet format within organized, date-stamped directories.
- **State Tracking**: Maintains a record of processed videos to avoid redundant work.
- **Single-Video Analysis**: Includes Jupyter notebooks for deep-dive analysis of individual videos.

## Project Structure

```
.
├── main.py                 # Main application entry point
├── youtube_client.py       # Handles interaction with yt-dlp
├── parsers.py              # Parses VTT and JSON data into pandas DataFrames
├── storage.py              # Manages file saving and state tracking
├── config.py               # Configuration settings (create this file)
├── analysis.ipynb          # Notebook for single-video analysis
├── data/                   # Directory where archived data is stored
├── processed_videos.txt    # Tracks IDs of processed videos
└── tests.py                # Unit tests
```

## Dependencies

The project uses Python 3 and relies on the following external libraries:

- `yt-dlp`: Command-line tool for downloading data from YouTube. Must be installed and available in your system's PATH.
- `pandas`: For data manipulation and analysis.
- `webvtt-py`: For parsing VTT subtitle files.

All Python dependencies are listed in `pyproject.toml`.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd youtube-live-transcript-archiver
    ```

2.  **Install Python dependencies**:
    ```bash
    # Using uv (recommended)
    uv sync

    # Or using pip
    pip install -r requirements.txt .
    ```

3.  **Install yt-dlp**:
    ```bash
    pip install yt-dlp
    ```
    Ensure `yt-dlp` is in your system's PATH.

## Configuration

Create a `config.py` file in the root directory with the following settings:

```python
# config.py

# The YouTube Channel ID to monitor.
# Find this in the channel's URL: https://www.youtube.com/channel/THIS_IS_THE_ID
YOUTUBE_CHANNEL_ID = "UC..."

# The number of recent livestreams to check on each run.
MAX_VIDEO_LOOKBACK = 5

# The yt-dlp executable. Change if using a custom path.
YTDLP_EXECUTABLE = "yt-dlp"
```

## Usage

### 1. Automatic Monitoring

Run the main application to monitor the configured channel for new livestreams:

```bash
python main.py
```

On each run, the application will:
1.  Check the most recent `MAX_VIDEO_LOOKBACK` livestreams from the channel.
2.  Skip any videos already processed.
3.  For new videos, attempt to download and process both the transcript and live chat.
4.  Save the processed data to the `data/` directory and mark the video as processed.

### 2. Single-Video Analysis

The project includes Jupyter notebooks for analyzing a single video in-depth.

-   **`analysis.ipynb`**: A comprehensive notebook for analyzing chat activity, user engagement, and keyword correlations. It's designed for ad-hoc, single-video studies.

To use it:
1.  Open the notebook in Jupyter.
2.  Set the `YOUTUBE_VIDEO_URL` variable at the top of the notebook.
3.  Run all cells to perform the analysis and generate visualizations.

## Data Output

Processed data is saved in the `data/` directory, with each video in its own folder:

```
data/
└── YYYYMMDD_<VIDEO_ID>/
    ├── metadata.json
    ├── transcript.parquet
    └── chat.parquet
```

-   **`metadata.json`**: Contains video ID, title, and processing timestamp.
-   **`transcript.parquet`**: A pandas DataFrame with cleaned transcript text and timestamps.
-   **`chat.parquet`**: A pandas DataFrame with chat messages, authors, timestamps, and SuperChat information.

## Running Tests

Execute the test suite to verify functionality:

```bash
python -m unittest tests.py
```