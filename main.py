import sys
from config import get_config
from src.ingest import ContentIngester
from src.analyze import process_chat_signals
from src.video import get_video_metadata, normalize_clip
from src.export import generate_professional_edl
from src import parsers
from src.reporting import ReportGenerator
from src.utils import Logger, AnalysisReporter
import os
import argparse

# --- RELIABILITY CONSTANTS ---
DOWNLOAD_BUFFER = 10  # Seconds to grab before/after to ensure we get the keyframe
MERGE_THRESHOLD = 30  # If clips are closer than 30s, merge them


def apply_time_slice(chat_df, start_time=None, end_time=None):
    """Apply time slicing to chat data."""
    if chat_df.empty:
        return chat_df

    mask = []
    if start_time is not None:
        mask.append(chat_df["offset_seconds"] >= start_time)
    if end_time is not None:
        mask.append(chat_df["offset_seconds"] <= end_time)

    if mask:
        combined_mask = mask[0]
        for m in mask[1:]:
            combined_mask &= m
        return chat_df[combined_mask].copy()

    return chat_df


def robust_merge_ranges(times, pad_pre, pad_post):
    """Merge highlights if they are close to maximize viewer context."""
    if not times:
        return []
    # Add Padding
    ranges = sorted([(t - pad_pre, t + pad_post) for t in times])

    merged = []
    curr_start, curr_end = ranges[0]

    for start, end in ranges[1:]:
        # If the gap between clips is small (or negative), merge them
        if start <= (curr_end + MERGE_THRESHOLD):
            curr_end = max(curr_end, end)
        else:
            merged.append((max(0, curr_start), curr_end))
            curr_start, curr_end = start, end

    merged.append((max(0, curr_start), curr_end))
    return merged


def run_clip_generator(
    url,
    dry_run=False,
    start_time=None,
    end_time=None,
    report_format=None,
    include_raw_data=None,
    compress_json=None,
    include_charts=None,
):
    """Enhanced pipeline with comprehensive error handling."""
    try:
        Logger.info(
            f"Starting pipeline for URL: {url}",
            {"dry_run": dry_run, "start_time": start_time, "end_time": end_time},
        )

        # Validate URL
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        cfg = get_config(url, start_time, end_time)
        cfg.DRY_RUN = dry_run

        # Override config with CLI arguments if provided
        if report_format is not None:
            cfg.REPORT_FORMAT = report_format
        if include_raw_data is not None:
            cfg.REPORT_INCLUDE_RAW_DATA = include_raw_data
        if compress_json is not None:
            cfg.REPORT_COMPRESS_JSON = compress_json
        if include_charts is not None:
            cfg.HTML_INCLUDE_CHARTS = include_charts

        # Initialize analysis reporter
        reporter = AnalysisReporter(cfg.OUTPUT_DIR)
        reporter.start_run(url, dry_run)
        reporter.log_configuration(cfg.model_dump())

        Logger.info(f"Initiating pipeline for: {url}")
        if cfg.DRY_RUN:
            Logger.dry_run("Mode active. No video will be downloaded or processed.")

        # Phase 1: Metadata and chat analysis (always runs)
        try:
            Logger.info("Phase 1: Downloading metadata and chat")
            ingester = ContentIngester(cfg.OUTPUT_DIR)
            platform = "twitch" if "twitch.tv" in url else "youtube"

            # Extract video_id from the config OUTPUT_DIR to match actual file naming
            video_id = os.path.basename(cfg.OUTPUT_DIR)
            paths = ingester.download_chat_and_transcript(url, video_id)

            if not paths or not paths.get("chat"):
                Logger.warning("No chat data available for analysis")
                return

            chat_df = parsers.parse_chat_log(paths["chat"], platform=platform)

            if chat_df.empty:
                Logger.warning("Chat parsing resulted in empty dataset")
                # Don't return - continue with transcript analysis

            # Parse transcript if available
            transcript_df = None
            if paths.get("transcript") and os.path.exists(paths["transcript"]):
                try:
                    transcript_df = parsers.parse_transcript_vtt(paths["transcript"])
                    Logger.info(f"Transcript parsed: {len(transcript_df)} segments")
                except Exception as e:
                    Logger.warning(f"Failed to parse transcript: {e}")
                    reporter.log_error("Transcript parsing failed", e)

            # Apply time slicing if specified
            if start_time is not None or end_time is not None:
                original_chat_size = len(chat_df)
                chat_df = apply_time_slice(chat_df, start_time, end_time)
                Logger.info(
                    f"Time slicing applied: {original_chat_size} -> {len(chat_df)} chat messages"
                )

                if transcript_df is not None:
                    transcript_df = parsers.get_transcript_segment(
                        transcript_df,
                        float(start_time) if start_time is not None else None,
                        float(end_time) if end_time is not None else None,
                    )
                    Logger.info(
                        f"Transcript sliced: {len(transcript_df)} segments remain"
                    )

            # Log data summary
            reporter.log_data_summary(chat_df, transcript_df)

            # Log text replacements if any were applied
            if hasattr(cfg, "REPLACE_WORDS") and cfg.REPLACE_WORDS:
                reporter.log_processing_step(
                    "data_parsing_and_slicing",
                    {
                        "start_time": start_time,
                        "end_time": end_time,
                        "chat_messages": len(chat_df),
                        "transcript_segments": len(transcript_df)
                        if transcript_df is not None
                        else 0,
                        "text_replacements_enabled": True,
                    },
                )

        except Exception as e:
            Logger.error("Failed during metadata and chat analysis phase", e)
            return

        # Phase 2: Analysis
        try:
            Logger.info("Phase 2: Analyzing chat signals")
            reporter.log_processing_step(
                "chat_analysis_start",
                {
                    "rolling_window_min": cfg.ROLLING_WINDOW_MIN,
                    "spike_threshold": cfg.SPIKE_Z_SCORE_THRESHOLD,
                    "keywords": cfg.KEYWORDS,
                },
            )

            spike_seconds = process_chat_signals(
                chat_df, window_min=cfg.ROLLING_WINDOW_MIN
            )
            final_ranges = robust_merge_ranges(
                spike_seconds, cfg.PADDING_PRE_SEC, cfg.PADDING_POST_SEC
            )

            # Log highlights and get transcript context
            reporter.log_highlights(final_ranges, spike_seconds)
            if transcript_df is not None and cfg.INCLUDE_TRANSCRIPT_CONTEXT:
                for i, (start, end) in enumerate(final_ranges):
                    reporter.log_transcript_context(i + 1, start, end, transcript_df)

            reporter.log_processing_step(
                "chat_analysis_complete",
                {
                    "spikes_detected": len(spike_seconds),
                    "final_highlights": len(final_ranges),
                },
            )

            Logger.info(
                f"Analysis complete. Found {len(final_ranges)} highlight clusters."
            )

            if len(final_ranges) == 0:
                Logger.info("No highlights detected in stream")
                # Continue to generate reports with transcript data even if no highlights

        except Exception as e:
            Logger.error("Failed during signal analysis phase", e)
            return

        # 3. DOWNLOAD PHASE
        raw_files = []
        video_id = cfg.OUTPUT_DIR.split("/")[-1]
        buffered_ranges = [
            (s - DOWNLOAD_BUFFER, e + DOWNLOAD_BUFFER) for s, e in final_ranges
        ]

        reporter.log_processing_step(
            "download_phase_start",
            {
                "segments_count": len(buffered_ranges),
                "download_buffer": DOWNLOAD_BUFFER,
            },
        )

        if not cfg.DRY_RUN:
            try:
                Logger.info(f"Downloading {len(buffered_ranges)} video segments")
                raw_files = ingester.download_specific_clips(
                    url, video_id, buffered_ranges
                )

                if not raw_files:
                    Logger.error("No video clips were successfully downloaded")
                    reporter.log_error("No video clips downloaded")
                    return

                Logger.success(f"Successfully downloaded {len(raw_files)} video clips")
                reporter.log_processing_step(
                    "download_complete", {"files_downloaded": len(raw_files)}
                )

            except Exception as e:
                Logger.error(
                    "Failed to download video clips",
                    e,
                    {"url": url, "segments": len(buffered_ranges)},
                )
                reporter.log_error("Failed to download video clips", e)
                return

        # 4. PROCESSING LOOP
        Logger.info("Processing video clips for editor compatibility")
        processed_files = []

        for i, (start, end) in enumerate(final_ranges):
            duration = end - start
            Logger.info(f"Clip {i + 1}: {start}s to {end}s (Duration: {duration}s)")

            # --- DOWNLOAD STEP ---
            if cfg.DRY_RUN:
                dry_run_cmd = (
                    f'yt-dlp --download-ranges "{start - DOWNLOAD_BUFFER}-{end + DOWNLOAD_BUFFER}" '
                    f'--format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" '
                    f'--force-keyframes-at-cuts --output "{video_id}_raw_clip_{i:03d}.%(ext)s" '
                    f"{url}"
                )
                Logger.dry_run(
                    dry_run_cmd,
                    {"segment": i + 1, "start": start, "end": end},
                )
                reporter.log_command(
                    dry_run_cmd, f"dry_run_download_clip_{i + 1}", True
                )

            # --- TRANSCODE STEP ---
            if cfg.DRY_RUN:
                input_file = f"raw_clip_{i}.mp4"
                output_file = f"Highlight_{i}_Clean.mp4"
                ffmpeg_cmd = (
                    f"ffmpeg -i {input_file} -r 60 -c:v libx264 -crf 18 -preset fast "
                    f"-c:a aac -ar 48000 -strict experimental {output_file}"
                )
                Logger.dry_run(
                    ffmpeg_cmd,
                    {"segment": i + 1, "input": input_file, "output": output_file},
                )
                reporter.log_command(
                    ffmpeg_cmd, f"dry_run_transcode_clip_{i + 1}", True
                )
            else:
                raw_path = None
                try:
                    if i < len(raw_files):
                        raw_path = raw_files[i]
                        final_filename = f"Highlight_{i + 1:03d}_Clean.mp4"
                        final_path = os.path.join(cfg.OUTPUT_DIR, final_filename)

                        Logger.progress(
                            "Normalizing clips", i + 1, len(raw_files), final_filename
                        )
                        ffmpeg_cmd = f"ffmpeg -i {raw_path} -r 60 -c:v libx264 -crf 18 -preset fast -c:a aac -ar 48000 -strict experimental {final_path}"
                        success = normalize_clip(raw_path, final_path)

                        if success:
                            Logger.success(f"✓ Saved: {final_filename}")
                            processed_files.append(final_path)
                            reporter.log_command(
                                ffmpeg_cmd, f"normalize_clip_{i + 1}", True
                            )
                        else:
                            Logger.error(f"✗ Failed to normalize: {raw_path}")
                            reporter.log_command(
                                ffmpeg_cmd, f"normalize_clip_{i + 1}", False
                            )
                    else:
                        Logger.warning(
                            f"Skipping clip {i + 1} - no corresponding download"
                        )

                except Exception as e:
                    Logger.error(
                        f"Failed to normalize clip {i + 1}",
                        e,
                        {"input": raw_path if raw_path else "N/A"},
                    )

        # 5. EXPORT PHASE
        if not cfg.DRY_RUN and processed_files:
            video_path = None
            edl_path = None
            try:
                Logger.info("Generating EDL for video editors")
                video_path = raw_files[0]  # Use first clip for metadata
                meta = get_video_metadata(video_path)

                video_id = cfg.OUTPUT_DIR.split("/")[-1]
                edl_path = f"{cfg.OUTPUT_DIR}/{video_id}.edl"

                generate_professional_edl(
                    final_ranges, video_path, meta["fps"], edl_path
                )
                Logger.success(f"EDL generated: {edl_path}")
                reporter.log_processing_step(
                    "edl_generation",
                    {
                        "edl_path": edl_path,
                        "highlights_count": len(final_ranges),
                        "fps": meta["fps"],
                    },
                )

            except Exception as e:
                Logger.error(
                    "Failed to generate EDL",
                    e,
                    {
                        "video_path": video_path if video_path else "N/A",
                        "edl_path": edl_path if edl_path else "N/A",
                    },
                )
                reporter.log_error("Failed to generate EDL", e)
        elif cfg.DRY_RUN:
            video_id = cfg.OUTPUT_DIR.split("/")[-1]
            Logger.dry_run(
                f"EDL generation would create: {video_id}.edl with {len(final_ranges)} clips"
            )
            reporter.log_processing_step(
                "edl_dry_run", {"highlights_count": len(final_ranges)}
            )

        Logger.success(
            "Pipeline completed successfully",
            {
                "highlights_found": len(final_ranges),
                "dry_run": cfg.DRY_RUN,
                "platform": platform,
                "processed_clips": len(processed_files)
                if not cfg.DRY_RUN
                else "simulated",
            },
        )

        # Save analysis report
        if cfg.GENERATE_ANALYSIS_REPORT:
            try:
                # Prepare analysis data for the new reporting system
                analysis_data = {
                    "run_info": reporter.analysis_log.get("run_info", {}),
                    "configuration": cfg.model_dump(),
                    "data_summary": reporter.analysis_log.get("data_summary", {}),
                    "highlights": reporter.analysis_log.get("highlights", []),
                    "processing_steps": reporter.analysis_log.get(
                        "processing_steps", []
                    ),
                    "errors": reporter.analysis_log.get("errors", []),
                }

                # Add chat and transcript data if available
                if not chat_df.empty:
                    analysis_data["chat_data"] = chat_df.to_dict(orient="records")
                if transcript_df is not None and not transcript_df.empty:
                    analysis_data["transcript_data"] = transcript_df.to_dict(
                        orient="records"
                    )

                # Add transcript excerpts to highlights for better reporting
                transcript_contexts = reporter.analysis_log.get(
                    "transcript_contexts", []
                )
                for context in transcript_contexts:
                    highlight_id = context["highlight_id"]
                    # Find the corresponding highlight and add transcript excerpt
                    for highlight in analysis_data["highlights"]:
                        if highlight["id"] == highlight_id:
                            transcript_excerpt = "\n".join(
                                context["text_content"][:3]
                            )  # First 3 segments
                            highlight["transcript_excerpt"] = transcript_excerpt
                            break

                report_generator = ReportGenerator(cfg.OUTPUT_DIR, cfg.model_dump())
                generated_files = report_generator.generate_reports(analysis_data)

                for file_path in generated_files:
                    Logger.success(f"Analysis report saved: {file_path}")
            except Exception as e:
                Logger.error("Failed to save analysis report", e)

    except KeyboardInterrupt:
        Logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        Logger.error("Unexpected pipeline failure", e, {"url": url})
        sys.exit(1)


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream Highlight Clipper")
    parser.add_argument("url", help="YouTube or Twitch URL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform analysis but skip video processing",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="Start time in seconds (optional)",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="End time in seconds (optional)",
    )
    parser.add_argument(
        "--report-format",
        choices=["html", "json", "txt", "all"],
        default="all",
        help="Report format to generate (default: all)",
    )
    parser.add_argument(
        "--include-raw-data",
        action="store_true",
        help="Include raw chat and transcript data in reports",
    )
    parser.add_argument(
        "--compress-json",
        action="store_true",
        help="Compress JSON reports to reduce file size",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Disable charts in HTML reports",
    )

    args = parser.parse_args()

    # Note: CLI arguments will be applied when config is created in run_clip_generator

    run_clip_generator(
        args.url,
        dry_run=args.dry_run,
        start_time=args.start,
        end_time=args.end,
        report_format=args.report_format,
        include_raw_data=args.include_raw_data,
        compress_json=args.compress_json,
        include_charts=not args.no_charts,
    )
