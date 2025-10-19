# -*- coding: utf-8 -*-
"""
Module for handling file system operations like saving data and
tracking processed video IDs.
"""

import os
import json
import datetime
import pandas as pd

# --- Configuration ---
PROCESSED_VIDEOS_FILE = 'processed_videos.txt'
DATA_DIR = 'data'

def ensure_directories_exist():
    """Creates the base data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

def load_processed_ids():
    """Loads the set of already processed video IDs from the tracking file."""
    if not os.path.exists(PROCESSED_VIDEOS_FILE):
        return set()
    with open(PROCESSED_VIDEOS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def mark_id_as_processed(video_id):
    """Appends a video ID to the tracking file."""
    with open(PROCESSED_VIDEOS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{video_id}\n")

def save_data(video_id, video_title, data_type, df):
    """
    Saves the processed DataFrame to a .parquet file and creates a
    metadata.json file in a video-specific directory.
    
    Args:
        video_id (str): The YouTube video ID.
        video_title (str): The title of the video.
        data_type (str): 'transcript' or 'chat'.
        df (pd.DataFrame): The DataFrame to save.
    """
    # Create the directory name based on date and video ID
    date_str = datetime.datetime.now().strftime('%Y%m%d') # Switched to YYYYMMDD for better sorting
    video_folder_name = f"{date_str}_{video_id}"
    video_dir_path = os.path.join(DATA_DIR, video_folder_name)
    
    # Ensure the video-specific directory exists
    if not os.path.exists(video_dir_path):
        os.makedirs(video_dir_path)
        print(f"Created directory: {video_dir_path}")

    # --- Save Metadata ---
    metadata_path = os.path.join(video_dir_path, 'metadata.json')
    if not os.path.exists(metadata_path):
        metadata = {
            'videoId': video_id,
            'videoTitle': video_title,
            'processingTimestampUTC': datetime.datetime.utcnow().isoformat(),
            'folderName': video_folder_name
        }
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=4)
            print(f"Saved metadata to: {metadata_path}")
        except IOError as e:
            print(f"Error saving metadata to {metadata_path}: {e}")

    # --- Save DataFrame to Parquet ---
    parquet_filename = f"{data_type}.parquet"
    parquet_filepath = os.path.join(video_dir_path, parquet_filename)
    
    try:
        df.to_parquet(parquet_filepath, index=False)
        print(f"Successfully saved {data_type} DataFrame to: {parquet_filepath}")
    except Exception as e:
        print(f"Error saving DataFrame to {parquet_filepath}: {e}")

