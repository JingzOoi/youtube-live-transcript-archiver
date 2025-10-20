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
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        return result
    except FileNotFoundError:
        print("Error: 'yt-dlp' command not found. Is it installed and in your system's PATH?")
        return None
    except subprocess.CalledProcessError as e:
        # This is common (e.g., no subtitles found), so we log it but don't raise an exception
        print(f"yt-dlp command failed with exit code {e.returncode}. STDERR: {e.stderr.strip()}")
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
        '--flat-playlist',
        '--dump-single-json',
        f'--playlist-end={max_results}',
        "--sleep-interval", "1",
        "--max-sleep-interval", "5",
        channel_url
    ]
    print(f"Fetching recent videos from channel: {channel_id} to check for livestreams.")
    result = _run_ytdlp_command(command)
    if not result:
        return []

    try:
        data = json.loads(result.stdout)
        livestreams = []
        for entry in data.get('entries', []):
            if entry.get('title').endswith(' - Live'):
                live_entries = entry
                break
        for entry in live_entries.get('entries', []):
            if entry.get('live_status') == 'was_live':
                livestreams.append({
                    'id': entry['id'],
                    'title': entry['title']
                })
        else:
            print("No livestreams found.")
        print(f"Found {len(livestreams)} recent livestreams to process.")
        return livestreams
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON output from yt-dlp.")
        return []

def download_transcript(video_id):
    """
    Downloads a transcript to a temporary file.
    Returns the path to the temp file, or None if it fails.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Attempting to download transcript for video ID: {video_id}")
    
    # Create a temporary file with a specific name yt-dlp can use
    temp_dir = tempfile.gettempdir()
    temp_filepath_base = os.path.join(temp_dir, f"transcript_{video_id}")

    command = [
        YTDLP_EXECUTABLE, '--write-auto-sub', '--sub-lang', 'en', '--skip-download',
        '-o', temp_filepath_base, video_url
    ]
    
    result = _run_ytdlp_command(command)
    if not result:
        return None

    # Find the actual file yt-dlp created (e.g., transcript_VIDEOID.en.vtt)
    expected_file = f"{temp_filepath_base}.en.vtt"
    if os.path.exists(expected_file):
        print(f"Transcript downloaded to temporary file: {expected_file}")
        return expected_file
    
    print(f"No English transcript found for video ID: {video_id}")
    return None

def download_live_chat(video_id):
    """
    Downloads a live chat replay to a temporary file.
    Returns the path to the temp file, or None if it fails.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"Attempting to download live chat for video ID: {video_id}")
    
    temp_dir = tempfile.gettempdir()
    temp_filepath_base = os.path.join(temp_dir, f"chat_{video_id}")

    command = [
        YTDLP_EXECUTABLE, 
        '--skip-download', 
        '--write-sub', 
        '--sub-lang', 
        'live_chat', 
        '-o', temp_filepath_base, video_url
    ]
    
    result = _run_ytdlp_command(command)
    if not result:
        return None

    # Find the actual file yt-dlp created
    expected_file = f"{temp_filepath_base}.live_chat.json"
    if os.path.exists(expected_file):
        print(f"Live chat downloaded to temporary file: {expected_file}")
        return expected_file

    print(f"No live chat replay found for video ID: {video_id}")
    return None
