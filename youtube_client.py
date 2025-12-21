# -*- coding: utf-8 -*-
"""
Module for interacting with yt-dlp to fetch data from YouTube.
"""

import subprocess
import json
import tempfile
import os
from config import YTDLP_EXECUTABLE


def _run_ytdlp_command(command):
    """A helper function to run a yt-dlp command and handle common errors."""
    try:
        print(f"  [RUNNING COMMAND]: {' '.join(command)}")
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return result
    except FileNotFoundError:
        print(
            "Error: 'yt-dlp' command not found. Is it installed and in your system's PATH?"
        )
        return None
    except subprocess.CalledProcessError as e:
        # This is common (e.g., no subtitles found), so we log it but don't raise an exception
        print(
            f"yt-dlp command failed with exit code {e.returncode}. STDERR: {e.stderr.strip()}"
        )
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running yt-dlp: {e}")
        return None


def get_recent_livestreams(channel_id, max_results=5):
    """
    Fetches details for the most recent livestreams using yt-dlp.
    """
    channel_url = f"https://www.youtube.com/channel/{channel_id}"
    command = [
        YTDLP_EXECUTABLE,
        "--flat-playlist",
        "--dump-single-json",
        f"--playlist-end={max_results}",
        "--sleep-interval",
        "1",
        "--max-sleep-interval",
        "5",
        channel_url,
    ]
    print(
        f"Fetching recent videos from channel: {channel_id} to check for livestreams."
    )
    result = _run_ytdlp_command(command)
    if not result:
        return []

    try:
        data = json.loads(result.stdout)
        livestreams = []
        live_entries = None
        for entry in data.get("entries", []):
            if entry.get("title").endswith(" - Live"):
                live_entries = entry
                break

        if live_entries:
            for entry in live_entries.get("entries", []):
                if entry.get("live_status") == "was_live":
                    livestreams.append({"id": entry["id"], "title": entry["title"]})
        else:
            print("No livestreams found.")
        print(f"Found {len(livestreams)} recent livestreams to process.")
        return livestreams
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON output from yt-dlp.")
        return []


def download_transcript(video_id, output_dir=None):
    """
    Downloads a transcript to a temporary file.
    Returns the path to the temp file, or None if it fails.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Attempting to download transcript for video ID: {video_id}")

    # Create a temporary file with a specific name yt-dlp can use
    dl_dir = tempfile.gettempdir() if not output_dir else output_dir
    dl_filepath_base = os.path.join(dl_dir, f"transcript_{video_id}")
    expected_file = f"{dl_filepath_base}.en.vtt"

    # Check if the file already exists
    if os.path.exists(expected_file):
        print(f"Found already existing file in {expected_file}.")
        return expected_file

    command = [
        YTDLP_EXECUTABLE,
        "--write-auto-sub",
        "--sub-lang",
        "en",
        "--skip-download",
        "-o",
        dl_filepath_base,
        video_url,
    ]

    result = _run_ytdlp_command(command)
    if not result:
        return None

    # Find the actual file yt-dlp created (e.g., transcript_VIDEOID.en.vtt)
    if os.path.exists(expected_file):
        print(f"Transcript downloaded to temporary file: {expected_file}")
        return expected_file

    print(f"No English transcript found for video ID: {video_id}")
    return None


def download_live_chat(video_id, output_dir=None):
    """
    Downloads a live chat replay to a temporary file.
    Returns the path to the temp file, or None if it fails.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Attempting to download live chat for video ID: {video_id}")

    dl_dir = tempfile.gettempdir() if not output_dir else output_dir
    dl_filepath_base = os.path.join(dl_dir, f"chat_{video_id}")
    expected_file = f"{dl_filepath_base}.live_chat.json"

    if os.path.exists(expected_file):
        print(f"Found already existing file in {expected_file}.")
        return expected_file

    command = [
        YTDLP_EXECUTABLE,
        "--skip-download",
        "--write-sub",
        "--sub-lang",
        "live_chat",
        "-o",
        dl_filepath_base,
        video_url,
    ]

    result = _run_ytdlp_command(command)
    if not result:
        return None

    # Find the actual file yt-dlp created
    if os.path.exists(expected_file):
        print(f"Live chat downloaded to temporary file: {expected_file}")
        return expected_file

    print(f"No live chat replay found for video ID: {video_id}")
    return None


def normalize_for_resolve(input_path):
    output_path = input_path.replace(".mp4", "_resolve.mp4")

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-x264-params", "keyint=60:min-keyint=60:scenecut=0",
        "-c:a", "aac",
        "-ar", "48000",
        "-movflags", "+faststart",
        output_path,
    ]

    subprocess.run(command, check=True)
    return output_path


def download_video(video_id, output_dir, download_sections=None, video_name=None):
    """
    Downloads a YouTube video to the specified output directory.

    Args:
        video_id (str): The YouTube video ID
        output_dir (str): Directory to save the downloaded video
        download_sections (list, optional): List of time sections to download
                                           in format [(start_time, end_time), ...]
                                           Times should be in HH:MM:SS format

    Returns:
        str: Path to the downloaded video file, or None if it fails
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Attempting to download video for video ID: {video_id}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Base filename for the video
    dl_filepath_base = os.path.join(output_dir, f"video_{video_id}") if video_name is None else os.path.join(output_dir, video_name)

    # Build yt-dlp command
    command = [
        YTDLP_EXECUTABLE,
        "--format",
        "best[height<=1080][ext=mp4][vcodec^=avc1]+(bestaudio[ext=m4a])",
        "--merge-output-format",
        "mp4",
        "-o",
        f"{dl_filepath_base}.%(ext)s",
        video_url,
    ]

    # Add section download if specified
    if download_sections:
        # For multiple sections, we'll need to download each separately
        # For now, handle single section
        if len(download_sections) == 1:
            start_time, end_time = download_sections[0]
            command.extend(["--download-sections", f"*{start_time}-{end_time}"])
            print(f"Downloading section from {start_time} to {end_time}")
        else:
            print("Multiple sections not yet supported, downloading full video")

    if os.path.exists(f"{dl_filepath_base}.mp4"):
        result = f"{dl_filepath_base}.mp4"
    else:
        result = _run_ytdlp_command(command)

    if not result:
        return None

    # Find the downloaded file (yt-dlp adds extension)
    for ext in ["mp4", "webm", "mkv"]:
        video_file = f"{dl_filepath_base}.{ext}"
        if os.path.exists(video_file):
            print(f"Video downloaded to: {video_file}")
            # if download_sections:
            #     video_file = normalize_for_resolve(video_file)
            return video_file

    print(f"Video download failed for video ID: {video_id}")
    return None
