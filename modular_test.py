import os
import pandas as pd
from src import parsers, analyze, export, utils
import youtube_client

# --- Configuration (Minimal Slice for Testing) ---
YOUTUBE_ID = "YKPHTUr3gNA"
OUTPUT_DIR = f"./data/{YOUTUBE_ID}_modular_test"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Analysis Window: 20:00 to 25:00
START_SEC = 20 * 60
END_SEC = 25 * 60

print(f"--- Starting Modular Integration Test for {YOUTUBE_ID} ---")

# 1. Ingest
print("1. Downloading & Parsing...")
transcript_file = youtube_client.download_transcript(YOUTUBE_ID)
chat_file = youtube_client.download_live_chat(YOUTUBE_ID)

df_transcript = parsers.parse_transcript_vtt(transcript_file)
df_chat = parsers.parse_youtube_chat_json(chat_file)

# 2. Slice
print(f"2. Slicing to {START_SEC}-{END_SEC}s...")
t_mask = (df_transcript['offset_start_seconds'] >= START_SEC) & (df_transcript['offset_end_seconds'] <= END_SEC)
c_mask = (df_chat['offset_seconds'] >= START_SEC) & (df_chat['offset_seconds'] <= END_SEC)

df_transcript_slice = df_transcript[t_mask].copy()
df_chat_slice = df_chat[c_mask].copy()

# 3. Analyze
print("3. running Analysis...")
# Note: Since the slice is small, highlights might not trigger without low threshold
highlights = analyze.process_chat_signals(
    df_chat_slice, 
    threshold_multiplier=0.5 # Lowered for testing on small slice
)

print(f"   Detected {len(highlights)} highlights.")

# 4. Export
print("4. Exporting...")
# A. Basic EDL for the whole slice
edl_path = os.path.join(OUTPUT_DIR, "test_slice.edl")
export.generate_basic_edl(
    [(START_SEC, END_SEC)], 
    edl_path, 
    YOUTUBE_ID, 
    offset_seconds=START_SEC
)

# B. Export Jobs for detected highlights (if any)
for i, (h_start, h_end) in enumerate(highlights, 1):
    job_name = f"HIGHLIGHT_{i:03d}"
    summary = export.process_export_job(
        job_name=job_name,
        start_sec=h_start,
        end_sec=h_end,
        output_dir=OUTPUT_DIR,
        youtube_id=YOUTUBE_ID,
        transcript_df=df_transcript,
        chat_df=df_chat,
        download_video=False # Skip video download in test to save time
    )
    print(f"   Job {job_name}: {summary}")

print(f"\n✓ Test Complete. Files saved to {OUTPUT_DIR}")
