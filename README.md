# Youtube Live Clip Generator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Status](https://img.shields.io/badge/Status-Production%20Ready-green) ![Platform](https://img.shields.io/badge/Platform-YouTube%20%7C%20Twitch-red)

A production-grade automation pipeline that identifies, extracts, and engineers broadcast-ready clips from long-form YouTube and Twitch streams. 

Unlike simple scripts that download entire videos, this engine uses **Rolling Z-Score analysis** to detect chat anomalies, performs **partial range requests** to save bandwidth, and enforces **Constant Frame Rate (CFR)** standards for seamless integration with DaVinci Resolve and Premiere Pro.

## 🚀 Key Features

*   **Multi-Platform Ingestion:** Seamlessly handles YouTube VODs and Twitch Replays.
*   **Robust Signal Processing:** Uses adaptive Rolling Z-Score analysis to detect highlights. It adjusts to the stream's baseline, ensuring "raids" or viral moments don't skew the detection threshold for the rest of the video.
*   **Bandwidth Efficient:** Downloads *only* the highlight segments (plus safety buffers) using HLS range requests. A 10-hour stream yields 500MB of clips, not 50GB of raw video.
*   **Editor-Ready Output:** 
    *   Transcodes clips to standard H.264/AAC with strict Constant Frame Rate (CFR).
    *   Generates industry-standard **CMX 3600 EDLs** (Edit Decision Lists) via OpenTimelineIO.
*   **Safety & Testing:** Includes a "Dry Run" mode to simulate pipeline execution without touching video files.

## 🛠️ Architecture

The pipeline follows a strict ETL (Extract, Transform, Load) pattern:

```ascii
[Ingest]          [Analyze]           [Refine]           [Export]
   |                  |                   |                  |
   v                  v                   v                  v
Download       Parse Chat Logs      Merge Overlaps      Partial DL
Chat/Meta     & Calculate Z-Score   & Add Padding     (Force Keyframes)
   |                  |                   |                  |
   +------------------+-------------------+                  v
                                                     Normalize (FFmpeg)
                                                             |
                                                             v
                                                      Generate EDL
                                                      & Clean .mp4
```

Here is the updated **Installation** section tailored for **uv**.

### 📦 Installation

This project utilizes **[uv](https://github.com/astral-sh/uv)** for lightning-fast dependency management.

#### Prerequisites
1.  **FFmpeg:** Must be installed on your system and accessible via PATH.
    *   *Mac:* `brew install ffmpeg`
    *   *Windows:* `winget install ffmpeg`
    *   *Linux:* `sudo apt install ffmpeg`
2.  **uv:** [Install uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) if you haven't already.

#### Setup

```bash
# 1. Clone the repository
git clone https://github.com/JingzOoi/youtube-live-transcript-archiver.git
cd youtube-live-transcript-archiver

# 2. Create Virtual Environment (uv defaults to .venv)
uv venv

# 3. Activate Environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 4. Install Dependencies
uv pip install pandas numpy scipy yt-dlp vaderSentiment ffmpeg-python opentimelineio plotly pydantic
```

---

*Note: If you prefer `requirements.txt`, you can generate one using `uv pip compile` or simply run `uv pip install -r requirements.txt` if provided.*


## 🖥️ Usage

### 1. The Clip Generator (Production Mode)
The main entry point. It scans the URL, detects highlights, and downloads the finalized clips to the `./data` directory.

```bash
python main.py https://www.youtube.com/watch?v=VIDEO_ID
```

### 2. Dry Run (Test Mode)
Highly recommended before processing long streams. This runs the ingestion and analysis but **skips** the video download/transcode steps. It prints the FFmpeg commands it *would* have run.

```bash
python main.py https://www.twitch.tv/videos/VIDEO_ID --dry-run
```

### 3. Visualization Workbench
Open `visualization_workbench.ipynb` in VS Code or Jupyter.
*   Interactively visualize the chat volume vs. the Z-Score baseline.
*   Read chat logs at specific timestamps to verify context.
*   Test time-slicing (e.g., "Analyze only hour 2 to hour 4").

## ⚙️ Configuration

Settings can be tuned in `config.py` to adjust sensitivity.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `ROLLING_WINDOW_MIN` | `20` | The "Memory" of the algorithm. Look back 20 mins to determine baseline. |
| `SPIKE_Z_SCORE` | `3.0` | Sensitivity. Higher = fewer, more intense highlights. |
| `PADDING_PRE_SEC` | `120` | Seconds of context to capture *before* the spike. |
| `PADDING_POST_SEC` | `60` | Seconds of context to capture *after* the spike. |
| `MERGE_THRESHOLD` | `30` | If two highlights are < 30s apart, merge them into one clip. |

## 📂 Project Structure

```text
stream-highlight-engine/
├── data/                  # Output directory (Ignored by Git)
├── src/
│   ├── analyze.py         # Signal processing & Z-score logic
│   ├── ingest.py          # yt-dlp Python wrappers
│   ├── export.py          # OTIO EDL generation
│   ├── parsers.py         # JSON/VTT parsing logic
│   ├── video.py           # FFmpeg transcoding & Probing
│   └── utils.py           # Logging helpers
├── config.py              # Pydantic configuration models
├── main.py                # CLI Orchestrator
├── visualization.ipynb    # Interactive Analysis Notebook
└── README.md
```

## ⚠️ Notes on Twitch Analysis
This engine uses **VADER** for sentiment analysis. While VADER is excellent for general English, Twitch chat relies heavily on emotes (`PogChamp`, `LULW`, `Kappa`).

*   **Current State:** The analyzer treats standard text ("LMAO", "OMG") as high sentiment.
*   **Future Roadmap:** We plan to inject a custom Lexicon into VADER to assign sentiment scores to common Twitch emotes (e.g., `Pog = +1.0`, `Sadge = -0.8`).
