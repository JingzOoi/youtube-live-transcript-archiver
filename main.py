# -*- coding: utf-8 -*-
"""
Main entry point for the YouTube Livestream Monitor application.
"""

import sys
from config import YOUTUBE_CHANNEL_ID
import youtube_client
import parsers
import storage

def main():
    """
    Main function to run the monitoring process.
    """
    print("--- Starting YouTube Livestream Monitor ---")
    
    if not YOUTUBE_CHANNEL_ID:
        print("Error: YOUTUBE_CHANNEL_ID is not set in config.py. Please set it and run again.")
        sys.exit(1)
        
    # 1. Ensure base directories are ready
    storage.ensure_directories_exist()
    
    # 2. Load IDs of videos that have already been processed
    processed_ids = storage.load_processed_ids()
    print(f"Found {len(processed_ids)} previously processed video IDs.")
    
    # 3. Get the 5 most recent videos from the channel
    print(f"Fetching recent videos for channel ID: {YOUTUBE_CHANNEL_ID}...")
    recent_videos = youtube_client.get_recent_livestreams(YOUTUBE_CHANNEL_ID)
    
    if not recent_videos:
        print("Could not fetch recent videos. Exiting.")
        return
        
    print(f"Found {len(recent_videos)} recent livestreams to check.")
    
    # 4. Process each new video
    new_videos_processed = 0
    for video in recent_videos:
        video_id = video['id']
        video_title = video['title']
        
        if video_id in processed_ids:
            print(f"\nSkipping video '{video_title}' (ID: {video_id}) - already processed.")
            continue
            
        print(f"\n>>> Processing NEW video: '{video_title}' (ID: {video_id})")
        new_videos_processed += 1
        
        transcript_processed = False
        chat_processed = False
        
        # --- Attempt to get and process transcript ---
        transcript_filepath = youtube_client.download_transcript(video_id)
        if transcript_filepath:
            parsed_transcript_df = parsers.parse_transcript_vtt(transcript_filepath)
            if not parsed_transcript_df.empty:
                storage.save_data(video_id, video_title, 'transcript', parsed_transcript_df)
                transcript_processed = True
            else:
                print(f"Parsing transcript for {video_id} resulted in empty data.")
        else:
            print(f"No transcript available yet for video: {video_id}")
            
        # --- Attempt to get and process live chat ---
        chat_filepath = youtube_client.download_live_chat(video_id)
        if chat_filepath:
            parsed_chat_df = parsers.parse_live_chat_json(chat_filepath)
            if not parsed_chat_df.empty:
                storage.save_data(video_id, video_title, 'chat', parsed_chat_df)
                chat_processed = True
            else:
                print(f"Parsing chat for {video_id} resulted in empty data.")
        else:
            print(f"No live chat replay available for video: {video_id}")
            
        # Mark as processed only if at least one data type was successfully saved
        if transcript_processed or chat_processed:
            storage.mark_id_as_processed(video_id)
            print(f"Finished processing and marked '{video_title}' as processed.")
        else:
            print(f"No data (transcript or chat) could be saved for '{video_title}'. Will retry on next run.")

    if new_videos_processed == 0:
        print("\nNo new videos to process.")
        
    print("\n--- YouTube Livestream Monitor Finished ---")


if __name__ == '__main__':
    main()

