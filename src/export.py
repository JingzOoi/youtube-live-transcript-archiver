import os
import pandas as pd
import opentimelineio as otio
from typing import List, Tuple, Optional
from .utils import convert_time


def generate_professional_edl(
    highlights: List[Tuple[float, float]],
    video_path: str,
    video_fps: int,
    output_path: str,
    title: str = "Highlights",
):
    """
    Generates a frame-accurate EDL using OpenTimelineIO. (Existing professional mode)
    """
    timeline = otio.schema.Timeline(name=title)
    track = otio.schema.Track(name="Video", kind=otio.schema.TrackKind.Video)
    timeline.tracks.append(track)

    media_url = f"file://{os.path.abspath(video_path)}"
    media_ref = otio.schema.ExternalReference(
        target_url=media_url,
        available_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, video_fps),
            duration=otio.opentime.RationalTime(100000, video_fps),
        ),
    )

    for i, (start_sec, end_sec) in enumerate(highlights):
        start_frame = int(start_sec * video_fps)
        duration_frames = int((end_sec - start_sec) * video_fps)

        src_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(start_frame, video_fps),
            duration=otio.opentime.RationalTime(duration_frames, video_fps),
        )

        clip = otio.schema.Clip(
            name=f"Highlight_{i+1:03d}", media_reference=media_ref, source_range=src_range
        )
        track.append(clip)

    otio.adapters.write_to_file(timeline, output_path, adapter_name="cmx_3600")
    print(f"✓ Professional EDL saved to: {output_path}")


def generate_basic_edl(
    ranges: List[Tuple[int, int]],
    output_path: str,
    youtube_id: str,
    offset_seconds: int = 0,
    fps: int = 60,
    source_matches_slice: bool = True,
):
    """
    Generates a simple text-based EDL with absolute stream time comments.
    """
    if not ranges:
        print("No ranges to export.")
        return

    calc_offset = offset_seconds if source_matches_slice else 0
    edl_lines = [f"TITLE: Highlights_{youtube_id}", "FCM: NON-DROP FRAME", ""]

    current_timeline_time = 0

    for i, (abs_start, abs_end) in enumerate(ranges, 1):
        duration_sec = abs_end - abs_start
        src_in = max(0, abs_start - calc_offset)
        src_out = max(0, abs_end - calc_offset)

        source_start_tc = convert_time(src_in, "timecode", fps)
        source_end_tc = convert_time(src_out, "timecode", fps)
        timeline_start_tc = convert_time(current_timeline_time, "timecode", fps)
        timeline_end_tc = convert_time(current_timeline_time + duration_sec, "timecode", fps)

        clip_name = f"HIGHLIGHT_{i:03d}"
        edl_lines.append(
            f"{i:03d}  {clip_name}     V     C        {source_start_tc} {source_end_tc} {timeline_start_tc} {timeline_end_tc}"
        )
        edl_lines.append(f"* FROM CLIP NAME: {clip_name}")
        edl_lines.append(f"* ABSOLUTE STREAM TIME: {convert_time(abs_start)} - {convert_time(abs_end)}")
        edl_lines.append("")

        current_timeline_time += duration_sec

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(edl_lines))
    print(f"✓ Basic EDL saved to: {output_path}")


def dataframe_to_srt(
    df: pd.DataFrame, output_path: str, ref_start_seconds: int = 0, ref_end_seconds: Optional[int] = None
) -> bool:
    """
    Convert transcript DataFrame to SRT Format with relative timing.
    """
    if df.empty:
        return False

    def seconds_to_srt_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            counter = 1
            for _, row in df.iterrows():
                abs_start = row["offset_start_seconds"]
                abs_end = row["offset_end_seconds"]

                if ref_end_seconds and abs_start >= ref_end_seconds:
                    continue
                if abs_end <= ref_start_seconds:
                    continue

                rel_start = max(0, abs_start - ref_start_seconds)
                rel_end = abs_end - ref_start_seconds
                if ref_end_seconds:
                    rel_end = min(rel_end, ref_end_seconds - ref_start_seconds)

                if rel_end > rel_start:
                    f.write(f"{counter}\n")
                    f.write(f"{seconds_to_srt_time(rel_start)} --> {seconds_to_srt_time(rel_end)}\n")
                    f.write(f"{row['text']}\n\n")
                    counter += 1
        return True
    except Exception as e:
        print(f"Error exporting SRT {output_path}: {e}")
        return False


def process_export_job(
    job_name: str,
    start_sec: int,
    end_sec: int,
    output_dir: str,
    youtube_id: str,
    transcript_df: pd.DataFrame = None,
    chat_df: pd.DataFrame = None,
    download_video: bool = False,
    youtube_client: Any = None,
) -> str:
    """
    Handles generation of Video, SRT, and Chat CSV for a time range.
    """
    actions = []
    video_path = os.path.join(output_dir, f"{job_name}.mp4")
    srt_path = os.path.join(output_dir, f"{job_name}.srt")
    csv_path = os.path.join(output_dir, f"{job_name}_chat.csv")

    # 1. Video
    if download_video and youtube_client:
        try:
            time_range = [(convert_time(start_sec), convert_time(end_sec))]
            youtube_client.download_video(
                youtube_id, output_dir=output_dir, video_name=job_name, download_sections=time_range
            )
            actions.append("Video")
        except Exception as e:
            print(f"Video Download Error: {e}")

    # 2. SRT
    if transcript_df is not None and not transcript_df.empty:
        t_mask = (transcript_df["offset_end_seconds"] > start_sec) & (
            transcript_df["offset_start_seconds"] < end_sec
        )
        job_transcript = transcript_df[t_mask].copy()
        if dataframe_to_srt(job_transcript, srt_path, start_sec, end_sec):
            actions.append("SRT")

    # 3. CSV
    if chat_df is not None and not chat_df.empty:
        c_mask = (chat_df["offset_seconds"] >= start_sec) & (chat_df["offset_seconds"] < end_sec)
        job_chat = chat_df[c_mask].copy()
        if not job_chat.empty:
            job_chat["time_offset"] = (job_chat["offset_seconds"] - start_sec).round(2)
            export_cols = ["time_offset", "author_name", "message"]
            if "superchat_amount" in job_chat.columns:
                export_cols.append("superchat_amount")
            job_chat[export_cols].to_csv(csv_path, index=False)
            actions.append(f"CSV ({len(job_chat)} msgs)")

    return ", ".join(actions) if actions else "No actions"