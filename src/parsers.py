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
from typing import Optional, List, Tuple, Dict
from config import AppConfig


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
    lines = raw_text.strip().split("\n")

    for line_content in lines:
        # Remove VTT inline timestamps like <00:00:00.000>
        cleaned_line = re.sub(r"<(\d{2}:){2}\d{2}\.\d{3}>", "", line_content)
        # Remove other VTT tags like <c> or <c.color>
        cleaned_line = re.sub(r"<\/?\w*[^>]*>", "", cleaned_line)
        # Remove bracketed annotations like [Music] or [&nbsp;__&nbsp;]
        cleaned_line = re.sub(r"\[[^\]]+\]", "", cleaned_line)
        # Replace &nbsp; with a space
        cleaned_line = cleaned_line.replace("&nbsp;", " ")
        # Strip leading/trailing whitespace and normalize multiple spaces
        cleaned_line = re.sub(r"\s+", " ", cleaned_line.strip())

        if cleaned_line:  # If this line has content after cleaning
            best_text_line = (
                cleaned_line  # Update, as later lines are often more complete
            )
    return best_text_line


def _consolidate_caption_df(df_initial):
    """
    Cleans text and consolidates cues from an initial DataFrame.
    """
    if df_initial.empty:
        return pd.DataFrame()

    # 1. Apply text replacements to each caption
    if hasattr(AppConfig, "REPLACE_WORDS"):
        df_initial["cleaned_text"] = df_initial["text"].apply(_clean_subtitle_text)
    else:
        df_initial["cleaned_text"] = df_initial["text"].apply(_clean_subtitle_text)

    # 2. Filter out rows that are empty after cleaning
    df_processed = df_initial[df_initial["cleaned_text"] != ""].copy()

    if df_processed.empty:
        return pd.DataFrame()

    # 3. Consolidate cues
    consolidated_rows = []

    # Initialize with the first valid cue
    first_cue = df_processed.iloc[0]
    consolidated_rows.append(
        {
            "start_time_str": first_cue["start_time_str"],
            "end_time_str": first_cue["end_time_str"],
            "start_seconds": first_cue["start_seconds"],
            "end_seconds": first_cue["end_seconds"],
            "text": first_cue["cleaned_text"],
        }
    )

    for i in range(1, len(df_processed)):
        current_row = df_processed.iloc[i]
        last_consolidated = consolidated_rows[-1]

        # Scenario 1: Current text is a superstring of last, and starts at/near same time
        if (
            current_row["cleaned_text"].startswith(last_consolidated["text"])
            and len(current_row["cleaned_text"]) > len(last_consolidated["text"])
            and abs(current_row["start_seconds"] - last_consolidated["start_seconds"])
            < 0.5
        ):
            last_consolidated["text"] = current_row["cleaned_text"]
            last_consolidated["end_time_str"] = current_row["end_time_str"]
            last_consolidated["end_seconds"] = current_row["end_seconds"]

        # --- NEW LOGIC ---
        # Scenario 2: Merge very short subsequent lines if they are close in time
        elif (
            len(current_row["cleaned_text"].split()) < 3
            and abs(current_row["start_seconds"] - last_consolidated["end_seconds"])
            < 1.0
        ):
            # Append the short text and update the end time
            last_consolidated["text"] += f" {current_row['cleaned_text']}"
            last_consolidated["end_time_str"] = current_row["end_time_str"]
            last_consolidated["end_seconds"] = current_row["end_seconds"]
        # -----------------

        # Scenario 3: New, distinct text or significant gap
        else:
            if (
                current_row["cleaned_text"] != last_consolidated["text"]
                or abs(current_row["start_seconds"] - last_consolidated["end_seconds"])
                >= 0.2
            ):
                consolidated_rows.append(
                    {
                        "start_time_str": current_row["start_time_str"],
                        "end_time_str": current_row["end_time_str"],
                        "start_seconds": current_row["start_seconds"],
                        "end_seconds": current_row["end_seconds"],
                        "text": current_row["cleaned_text"],
                    }
                )
            else:  # Similar text and time, likely a slight variation we can merge by extending
                last_consolidated["end_time_str"] = current_row["end_time_str"]
                last_consolidated["end_seconds"] = current_row["end_seconds"]

    return pd.DataFrame(consolidated_rows)


def apply_text_replacements(
    text: str, replacements: List[Tuple[str, str]]
) -> Tuple[str, Dict[str, int]]:
    """
    Apply text replacement rules to clean/standardize text content.

    Args:
        text: Original text content
        replacements: List of (original, replacement) tuples

    Returns:
        Tuple of (cleaned_text, replacement_stats)
    """
    if not text or not replacements:
        return text, {}

    cleaned_text = text
    replacement_stats = {}

    for original, replacement in replacements:
        # Case-insensitive replacement using regex
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        original_count = len(re.findall(original, cleaned_text))

        if original_count > 0:
            cleaned_text = pattern.sub(replacement, cleaned_text)
            replacement_stats[original] = {
                "count": original_count,
                "replacement": replacement,
            }

    return cleaned_text, replacement_stats


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
            captions_data.append(
                {
                    "start_time_str": caption.start,
                    "end_time_str": caption.end,
                    "start_seconds": caption.start_in_seconds,
                    "end_seconds": caption.end_in_seconds,
                    "text": caption.text,
                }
            )

        if not captions_data:
            return pd.DataFrame()

        df_initial = pd.DataFrame(captions_data)

        # 2. Process and consolidate the DataFrame
        df_final = _consolidate_caption_df(df_initial.copy())

        # Apply text replacements if configured
        try:
            from config import AppConfig

            if hasattr(AppConfig, "REPLACE_WORDS"):
                # Apply replacements to transcript text
                replacement_stats_list = []
                for idx, row in df_final.iterrows():
                    text_value = str(row["text"])  # Convert to string
                    cleaned_text, stats = apply_text_replacements(
                        text_value, AppConfig.REPLACE_WORDS
                    )
                    df_final.loc[idx, "text"] = cleaned_text
                    replacement_stats_list.append(stats)

                # Log replacement statistics (could be moved to analysis reporter)
                total_replacements = sum(len(stats) for stats in replacement_stats_list)
                if total_replacements > 0:
                    print(
                        f"Applied {total_replacements} text replacements to transcript"
                    )

        except ImportError:
            # Config not available, skip replacements
            pass

        # 3. Rename columns for consistency and clarity (already relative)
        df_final = df_final.rename(
            columns={
                "start_time_str": "start_time",
                "end_time_str": "end_time",
                "start_seconds": "offset_start_seconds",
                "end_seconds": "offset_end_seconds",
                "text": "text",
            }
        )

        print(
            f"Successfully parsed and consolidated VTT into a DataFrame with {len(df_final)} rows."
        )

        print(
            f"Successfully parsed and consolidated VTT into a DataFrame with {len(df_final)} rows."
        )
        return df_final[
            [
                "start_time",
                "end_time",
                "offset_start_seconds",
                "offset_end_seconds",
                "text",
            ]
        ]

    except Exception as e:
        print(f"An error occurred while parsing transcript file {filepath}: {e}")
        return pd.DataFrame()


def parse_youtube_chat_json(filepath: str) -> pd.DataFrame:
    """
    Parses a .live_chat.json file using official video offsets.
    """
    print(f"Parsing live chat JSON: {filepath}")
    try:
        chat_records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)

                    # 1. Extract Official Video Offset
                    replay_action = obj.get("replayChatItemAction", {})
                    video_offset_msec = replay_action.get("videoOffsetTimeMsec")

                    # Skip messages without an official video timestamp (helps remove some artifacts)
                    if not video_offset_msec:
                        continue

                    # Calculate seconds immediately
                    offset_seconds = int(video_offset_msec) / 1000.0

                    # Handle Actions
                    actions = replay_action.get("actions", [])
                    for action in actions:
                        item = action.get("addChatItemAction", {}).get("item", {})

                        msg_renderer = item.get("liveChatTextMessageRenderer")
                        paid_renderer = item.get("liveChatPaidMessageRenderer")
                        sticker_renderer = item.get("liveChatPaidStickerRenderer")

                        renderer = msg_renderer or paid_renderer or sticker_renderer
                        if not renderer:
                            continue

                        author_name = renderer.get("authorName", {}).get(
                            "simpleText", "Unknown"
                        )

                        message = ""
                        is_superchat = False
                        superchat_amount = None

                        if msg_renderer:
                            runs = msg_renderer.get("message", {}).get("runs", [])
                            message = "".join(
                                part.get("text", "") for part in runs
                            ).strip()

                        elif paid_renderer:
                            is_superchat = True
                            superchat_amount = paid_renderer.get(
                                "purchaseAmountText", {}
                            ).get("simpleText")
                            runs = paid_renderer.get("message", {}).get("runs", [])
                            message = "".join(
                                part.get("text", "") for part in runs
                            ).strip()

                        elif sticker_renderer:
                            is_superchat = True
                            superchat_amount = sticker_renderer.get(
                                "purchaseAmountText", {}
                            ).get("simpleText")
                            message = "[SUPERCHAT STICKER]"

                        if message:
                            chat_records.append(
                                {
                                    "offset_seconds": offset_seconds,
                                    "author_name": author_name,
                                    "message": message,
                                    "is_superchat": is_superchat,
                                    "superchat_amount": superchat_amount,
                                }
                            )

                except (json.JSONDecodeError, AttributeError):
                    continue

        if not chat_records:
            return pd.DataFrame()

        df_chat = pd.DataFrame(chat_records)
        # Ensure we sort by the official video offset
        df_chat = df_chat.sort_values("offset_seconds").reset_index(drop=True)

        # 2. Filter out negative offsets (Pre-stream / Waiting room)
        # Sometimes official offsets are negative if the user chatted before the recording started
        df_chat = df_chat[df_chat["offset_seconds"] >= 0].copy()

        if not df_chat.empty:
            df_chat["minute"] = (df_chat["offset_seconds"] // 60).astype(int)

            # Create human readable timestamp
            df_chat["offset_text"] = [
                str(datetime.timedelta(seconds=int(s)))
                for s in df_chat["offset_seconds"]
            ]

        if not chat_records:
            return pd.DataFrame()

        if not chat_records:
            return pd.DataFrame()

        df_chat = pd.DataFrame(chat_records)

        # Sort by timestamp
        df_chat = df_chat.sort_values("offset_seconds").reset_index(drop=True)

        # Filter out negative offsets (pre-stream messages)
        df_chat = df_chat[df_chat["offset_seconds"] >= 0].copy()

        if not df_chat.empty:
            # Add minute bucket
            df_chat["minute"] = (df_chat["offset_seconds"] // 60).astype(int)

            # Create human readable timestamp
            df_chat["offset_text"] = [
                str(datetime.timedelta(seconds=int(s)))
                for s in df_chat["offset_seconds"]
            ]

            # Reorder columns to match YouTube format
            df_chat = df_chat[
                [
                    "offset_seconds",
                    "minute",
                    "offset_text",
                    "author_name",
                    "message",
                    "is_superchat",
                    "superchat_amount",
                ]
            ]

        print(f"Parsed {len(df_chat)} Twitch chat messages.")
        # Ensure we return a DataFrame
        if isinstance(df_chat, pd.DataFrame):
            return df_chat
        else:
            return pd.DataFrame(df_chat)

    except Exception as e:
        print(f"Error parsing Twitch chat {filepath}: {e}")
        return pd.DataFrame()


def parse_twitch_chat_json(filepath: str) -> pd.DataFrame:
    """
    Parses a Twitch chat JSON file and returns a DataFrame with chat messages.

    Args:
        filepath (str): Path to the Twitch chat JSON file.

    Returns:
        pd.DataFrame: DataFrame containing chat messages with timestamps.
                     Returns an empty DataFrame if parsing fails.
    """
    print(f"Parsing Twitch chat JSON: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        comments = data.get("comments", [])
        if not comments:
            print("No comments found in Twitch chat JSON file.")
            return pd.DataFrame()

        chat_records = []
        for comment in comments:
            try:
                # Extract required fields
                offset_seconds = comment.get("content_offset_seconds")
                if offset_seconds is None:
                    continue

                commenter = comment.get("commenter", {})
                author_name = commenter.get("display_name", "Unknown")

                message_obj = comment.get("message", {})
                message = message_obj.get("body", "")
                bits_spent = message_obj.get("bits_spent", 0)
                user_color = message_obj.get("user_color")
                created_at = comment.get("created_at")

                # Skip empty messages
                if not message or not message.strip():
                    continue

                chat_records.append(
                    {
                        "offset_seconds": offset_seconds,
                        "author_name": author_name,
                        "message": message.strip(),
                        "bits_spent": bits_spent,
                        "user_color": user_color,
                        "created_at": created_at,
                    }
                )

            except (AttributeError, TypeError):
                # Skip malformed comments
                continue

        if not chat_records:
            return pd.DataFrame()

        df_chat = pd.DataFrame(chat_records)

        # Sort by timestamp
        df_chat = df_chat.sort_values("offset_seconds").reset_index(drop=True)

        # Filter out negative offsets (pre-stream messages)
        df_chat = df_chat[df_chat["offset_seconds"] >= 0].copy()

        if not df_chat.empty:
            # Add minute bucket
            df_chat["minute"] = (df_chat["offset_seconds"] // 60).astype(int)

            # Create human readable timestamp
            df_chat["offset_text"] = [
                str(datetime.timedelta(seconds=int(s)))
                for s in df_chat["offset_seconds"]
            ]

        # Reorder columns for consistency with YouTube parser
        column_order = [
            "offset_seconds",
            "minute",
            "offset_text",
            "author_name",
            "message",
            "bits_spent",
            "user_color",
            "created_at",
        ]
        # Only include columns that exist in the DataFrame
        existing_columns = [col for col in column_order if col in df_chat.columns]
        df_chat = df_chat[existing_columns].copy()

        print(f"Parsed {len(df_chat)} Twitch chat messages.")
        # Ensure we return a DataFrame
        if isinstance(df_chat, pd.DataFrame):
            return df_chat
        else:
            return pd.DataFrame(df_chat)

    except Exception as e:
        print(f"Error parsing Twitch chat {filepath}: {e}")
        return pd.DataFrame()


def get_transcript_segment(
    transcript_df: pd.DataFrame,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
):
    """
    Extracts transcript content within specified time range.

    Args:
        transcript_df: DataFrame with transcript data from parse_transcript_vtt()
        start_time: Start time in seconds (None = beginning)
        end_time: End time in seconds (None = end)

    Returns:
        pd.DataFrame: Filtered transcript with segments that overlap the time range
    """
    if transcript_df.empty:
        return pd.DataFrame()

    # If no time bounds, return full transcript
    if start_time is None and end_time is None:
        return transcript_df.copy()

    # Complex overlap logic for segments that span the time boundaries
    if start_time is not None and end_time is not None:
        overlap_condition = (
            (
                (transcript_df["offset_start_seconds"] >= start_time)
                & (transcript_df["offset_start_seconds"] <= end_time)
            )
            | (
                (transcript_df["offset_end_seconds"] >= start_time)
                & (transcript_df["offset_end_seconds"] <= end_time)
            )
            | (
                (transcript_df["offset_start_seconds"] <= start_time)
                & (transcript_df["offset_end_seconds"] >= end_time)
            )
        )
        return transcript_df[overlap_condition].copy()
    elif start_time is not None:
        return transcript_df[transcript_df["offset_end_seconds"] >= start_time].copy()
    elif end_time is not None:
        return transcript_df[transcript_df["offset_start_seconds"] <= end_time].copy()

    return transcript_df.copy()


def parse_chat_log(filepath, platform="youtube"):
    """
    Factory function to parse logs from different platforms
    into a Unified Data Model.
    """
    if platform == "youtube":
        return parse_youtube_chat_json(filepath)
    elif platform == "twitch":
        return parse_twitch_chat_json(filepath)
    else:
        raise ValueError(f"Unknown platform: {platform}")
