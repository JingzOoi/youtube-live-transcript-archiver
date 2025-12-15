# -*- coding: utf-8 -*-
"""
Module for interacting with TwitchDownloaderCLI to fetch data from Twitch.
"""

import subprocess
import tempfile
import os
from config import TWITCHDOWNLOADER_EXECUTABLE


def _run_twitchdownloader_command(command):
    """A helper function to run a TwitchDownloaderCLI command and handle common errors."""
    try:
        print(f"  [RUNNING COMMAND]: {' '.join(command)}")
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return result
    except FileNotFoundError:
        print(
            f"Error: '{TWITCHDOWNLOADER_EXECUTABLE}' command not found. Is it installed and in the correct path?"
        )
        return None
    except subprocess.CalledProcessError as e:
        print(
            f"TwitchDownloaderCLI command failed with exit code {e.returncode}. STDERR: {e.stderr.strip()}"
        )
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running TwitchDownloaderCLI: {e}")
        return None


def download_chat(vod_id, output_dir=None):
    """
    Downloads a Twitch VOD chat to a temporary file.
    Returns the path to the temp file, or None if it fails.

    Args:
        vod_id (str): The Twitch VOD ID
        output_dir (str, optional): Directory to save the chat file. Defaults to temp directory.

    Returns:
        str: Path to the downloaded chat JSON file, or None if it fails
    """
    print(f"Attempting to download chat for VOD ID: {vod_id}")

    # Create a temporary file with a specific name TwitchDownloaderCLI can use
    dl_dir = tempfile.gettempdir() if not output_dir else output_dir
    dl_filepath_base = os.path.join(dl_dir, f"twitch_chat_{vod_id}")
    expected_file = f"{dl_filepath_base}.json"

    # Check if the file already exists
    if os.path.exists(expected_file):
        print(f"Found already existing file in {expected_file}.")
        return expected_file

    command = [
        TWITCHDOWNLOADER_EXECUTABLE,
        "chatdownload",
        "--id",
        vod_id,
        "-o",
        expected_file,
    ]

    result = _run_twitchdownloader_command(command)
    if not result:
        return None

    # Find the actual file TwitchDownloaderCLI created
    if os.path.exists(expected_file):
        print(f"Chat downloaded to temporary file: {expected_file}")
        return expected_file

    print(f"No chat found for VOD ID: {vod_id}")
    return None


def download_video(vod_id, output_dir, download_sections=None, video_name=None):
    """
    Downloads a Twitch VOD video to the specified output directory.

    Args:
        vod_id (str): The Twitch VOD ID
        output_dir (str): Directory to save the downloaded video
        download_sections (list, optional): List of time sections to download
                                           in format [(start_time, end_time), ...]
                                           Times should be in HH:MM:SS format
        video_name (str, optional): Custom name for the video file

    Returns:
        str: Path to the downloaded video file, or None if it fails
    """
    print(f"Attempting to download video for VOD ID: {vod_id}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Base filename for the video
    if video_name is None:
        dl_filepath_base = os.path.join(output_dir, f"twitch_video_{vod_id}")
    else:
        dl_filepath_base = os.path.join(output_dir, video_name)

    # Build TwitchDownloaderCLI command
    command = [
        TWITCHDOWNLOADER_EXECUTABLE,
        "videodownload",
        "--id",
        vod_id,
        "-o",
        f"{dl_filepath_base}.mp4",
    ]

    # Add section download if specified (TwitchDownloaderCLI may not support this)
    if download_sections:
        # For multiple sections, we'll need to download each separately
        # For now, handle single section if supported
        if len(download_sections) == 1:
            start_time, end_time = download_sections[0]
            # Note: TwitchDownloaderCLI may not support section downloads like yt-dlp
            # This is a placeholder - actual implementation may need adjustment
            print(f"Section download requested from {start_time} to {end_time}")
            print(
                "Note: TwitchDownloaderCLI may not support time-based section downloads"
            )
        else:
            print("Multiple sections not yet supported, downloading full video")

    if os.path.exists(f"{dl_filepath_base}.mp4"):
        result = f"{dl_filepath_base}.mp4"
    else:
        result = _run_twitchdownloader_command(command)

    if not result:
        return None

    # Find the downloaded file (TwitchDownloaderCLI adds extension)
    for ext in ["mp4", "mkv", "ts"]:
        video_file = f"{dl_filepath_base}.{ext}"
        if os.path.exists(video_file):
            print(f"Video downloaded to: {video_file}")
            return video_file

    print(f"Video download failed for VOD ID: {vod_id}")
    return None
