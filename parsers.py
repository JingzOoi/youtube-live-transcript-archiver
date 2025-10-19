# -*- coding: utf-8 -*-
"""
Module for parsing raw data files into structured Python objects.
"""
import re
import json
import datetime
import pandas as pd
import webvtt
import io

def _clean_subtitle_text(raw_text):
    """
    Cleans subtitle text from a single caption's text content.
    If raw_text is multi-line, it picks the last non-empty line after cleaning.
    Removes VTT tags, [Music] annotations, etc.
    """
    if not raw_text:
        return ""

    best_text_line = ""
    # caption.text from webvtt-py can be a multi-line string
    lines = raw_text.strip().split('\n')

    for line_content in lines:
        # Remove VTT inline timestamps like <00:00:00.000>
        cleaned_line = re.sub(r'<(\d{2}:){2}\d{2}\.\d{3}>', '', line_content)
        # Remove other VTT tags like <c> or <c.color>
        cleaned_line = re.sub(r'<\/?\w*[^>]*>', '', cleaned_line)
        # Remove bracketed annotations like [Music] or [&nbsp;__&nbsp;]
        cleaned_line = re.sub(r'\[[^\]]+\]', '', cleaned_line)
        # Replace &nbsp; with a space
        cleaned_line = cleaned_line.replace('&nbsp;', ' ')
        # Strip leading/trailing whitespace and normalize multiple spaces
        cleaned_line = re.sub(r'\s+', ' ', cleaned_line.strip())

        if cleaned_line: # If this line has content after cleaning
            best_text_line = cleaned_line # Update, as later lines are often more complete
    return best_text_line

def _consolidate_caption_df(df_initial):
    """
    Cleans text and consolidates cues from an initial DataFrame.
    """
    if df_initial.empty:
        return pd.DataFrame(columns=['start_time_str', 'end_time_str', 'start_seconds', 'end_seconds', 'text'])

    # 1. Clean the text for each caption
    df_initial['cleaned_text'] = df_initial['text'].apply(_clean_subtitle_text)

    # 2. Filter out rows that are empty after cleaning
    df_processed = df_initial[df_initial['cleaned_text'] != ""].copy()

    if df_processed.empty:
        return pd.DataFrame(columns=['start_time_str', 'end_time_str', 'start_seconds', 'end_seconds', 'text'])

    # 3. Consolidate cues
    consolidated_rows = []

    # Initialize with the first valid cue
    first_cue = df_processed.iloc[0]
    consolidated_rows.append({
        'start_time_str': first_cue['start_time_str'],
        'end_time_str': first_cue['end_time_str'],
        'start_seconds': first_cue['start_seconds'],
        'end_seconds': first_cue['end_seconds'],
        'text': first_cue['cleaned_text']
    })

    for i in range(1, len(df_processed)):
        current_row = df_processed.iloc[i]
        last_consolidated = consolidated_rows[-1]

        # Scenario 1: Current text is a superstring of last, and starts at/near same time
        if (current_row['cleaned_text'].startswith(last_consolidated['text']) and
            len(current_row['cleaned_text']) > len(last_consolidated['text']) and
            abs(current_row['start_seconds'] - last_consolidated['start_seconds']) < 0.5):
            last_consolidated['text'] = current_row['cleaned_text']
            last_consolidated['end_time_str'] = current_row['end_time_str']
            last_consolidated['end_seconds'] = current_row['end_seconds']
        
        # --- NEW LOGIC ---
        # Scenario 2: Merge very short subsequent lines if they are close in time
        elif (len(current_row['cleaned_text'].split()) < 3 and
              abs(current_row['start_seconds'] - last_consolidated['end_seconds']) < 1.0):
            # Append the short text and update the end time
            last_consolidated['text'] += f" {current_row['cleaned_text']}"
            last_consolidated['end_time_str'] = current_row['end_time_str']
            last_consolidated['end_seconds'] = current_row['end_seconds']
        # -----------------

        # Scenario 3: New, distinct text or significant gap
        else:
            if (current_row['cleaned_text'] != last_consolidated['text'] or
                abs(current_row['start_seconds'] - last_consolidated['end_seconds']) >= 0.2):
                consolidated_rows.append({
                    'start_time_str': current_row['start_time_str'],
                    'end_time_str': current_row['end_time_str'],
                    'start_seconds': current_row['start_seconds'],
                    'end_seconds': current_row['end_seconds'],
                    'text': current_row['cleaned_text']
                })
            else: # Similar text and time, likely a slight variation we can merge by extending
                last_consolidated['end_time_str'] = current_row['end_time_str']
                last_consolidated['end_seconds'] = current_row['end_seconds']

    return pd.DataFrame(consolidated_rows)


def parse_transcript_vtt(filepath):
    """
    Parses a .vtt transcript file and returns a cleaned, consolidated DataFrame
    with timestamps relative to the video start.
    
    Args:
        filepath (str): The path to the .vtt file.

    Returns:
        pd.DataFrame: A DataFrame containing the transcript data.
                      Returns an empty DataFrame if parsing fails or file is empty.
    """
    print(f"Parsing VTT transcript file with pandas-based logic: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vtt_content = f.read()

        # 1. Load initial captions into a list
        captions_data = []
        vtt_buffer = io.StringIO(vtt_content)
        for caption in webvtt.read_buffer(vtt_buffer):
            captions_data.append({
                "start_time_str": caption.start,
                "end_time_str": caption.end,
                "start_seconds": caption.start_in_seconds,
                "end_seconds": caption.end_in_seconds,
                "text": caption.text
            })
        
        if not captions_data:
            return pd.DataFrame()

        df_initial = pd.DataFrame(captions_data)
        
        # 2. Process and consolidate the DataFrame
        df_final = _consolidate_caption_df(df_initial.copy())

        if df_final.empty:
            return pd.DataFrame()

        # 3. Rename columns for consistency and clarity (already relative)
        df_final = df_final.rename(columns={
            'start_time_str': 'start_time',
            'end_time_str': 'end_time',
            'start_seconds': 'offset_start_seconds',
            'end_seconds': 'offset_end_seconds'
        })
        
        print(f"Successfully parsed and consolidated VTT into a DataFrame with {len(df_final)} rows.")
        return df_final[['start_time', 'end_time', 'offset_start_seconds', 'offset_end_seconds', 'text']]

    except Exception as e:
        print(f"An error occurred while parsing transcript file {filepath}: {e}")
        return pd.DataFrame()

def parse_live_chat_json(filepath):
    """
    Parses a .live_chat.json (JSON Lines) file into a structured DataFrame
    with timestamps relative to the stream start, identifying superchats.

    Args:
        filepath (str): The path to the .live_chat.json file.

    Returns:
        pd.DataFrame: A DataFrame containing the chat data.
                      Returns an empty DataFrame if parsing fails or file is empty.
    """
    print(f"Parsing live chat JSON file with superchat detection: {filepath}")
    try:
        chat_records = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    actions = obj.get("replayChatItemAction", {}).get("actions", [])
                    for action in actions:
                        item = action.get("addChatItemAction", {}).get("item", {})
                        
                        # Determine the type of renderer
                        msg_renderer = item.get("liveChatTextMessageRenderer")
                        paid_renderer = item.get("liveChatPaidMessageRenderer")
                        sticker_renderer = item.get("liveChatPaidStickerRenderer")
                        
                        renderer = msg_renderer or paid_renderer or sticker_renderer
                        if not renderer:
                            continue

                        # --- Extract common data ---
                        timestamp_usec = int(renderer.get("timestampUsec", 0))
                        timestamp_sec = timestamp_usec // 1_000_000
                        author_name = renderer.get("authorName", {}).get("simpleText", "Unknown Author")
                        author_id = renderer.get("authorExternalChannelId")

                        # --- Initialize default values ---
                        message = ""
                        is_superchat = False
                        superchat_amount = None

                        # --- Process based on renderer type ---
                        if msg_renderer:
                            message_runs = msg_renderer.get("message", {}).get("runs", [])
                            message = "".join(part.get("text", "") for part in message_runs).strip()
                        
                        elif paid_renderer:
                            is_superchat = True
                            superchat_amount = paid_renderer.get("purchaseAmountText", {}).get("simpleText")
                            message_runs = paid_renderer.get("message", {}).get("runs", [])
                            message = "".join(part.get("text", "") for part in message_runs).strip()

                        elif sticker_renderer:
                            is_superchat = True
                            superchat_amount = sticker_renderer.get("purchaseAmountText", {}).get("simpleText")
                            message = "[SUPERCHAT STICKER]"

                        if message:
                            chat_records.append({
                                'absolute_timestamp_seconds': timestamp_sec,
                                'author_name': author_name,
                                'author_id': author_id,
                                'message': message,
                                'is_superchat': is_superchat,
                                'superchat_amount': superchat_amount
                            })

                except (json.JSONDecodeError, AttributeError):
                    # Skip malformed lines or lines without the expected structure
                    continue
        
        if not chat_records:
            return pd.DataFrame()

        df_chat = pd.DataFrame(chat_records)
        df_chat = df_chat.sort_values("absolute_timestamp_seconds").reset_index(drop=True)

        # --- Normalize to be relative to stream start ---
        if not df_chat.empty:
            stream_start_time = df_chat["absolute_timestamp_seconds"].min()
            df_chat["offset_seconds"] = df_chat["absolute_timestamp_seconds"] - stream_start_time
            df_chat["offset_text"] = df_chat["offset_seconds"].apply(
                lambda s: str(datetime.timedelta(seconds=int(s)))
            )
            # Reorder and drop absolute timestamp column
            df_chat = df_chat[[
                'offset_seconds', 
                'offset_text', 
                'author_name', 
                'author_id', 
                'message', 
                'is_superchat', 
                'superchat_amount'
            ]]
        
        print(f"Successfully parsed and normalized {len(df_chat)} chat messages into a DataFrame.")
        return df_chat

    except (IOError, Exception) as e:
        print(f"An error occurred while parsing chat file {filepath}: {e}")
        return pd.DataFrame()

