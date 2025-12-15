import sys
from config import get_config
from src.ingest import ContentIngester
from src.analyze import process_chat_signals
from src.video import get_video_metadata, normalize_clip
from src.export import generate_professional_edl
from src import parsers
import os
import argparse
from src.utils import Logger

# --- RELIABILITY CONSTANTS ---
DOWNLOAD_BUFFER = 10  # Seconds to grab before/after to ensure we get the keyframe
MERGE_THRESHOLD = 30  # If clips are closer than 30s, merge them


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


def run_clip_generator(url, dry_run=False):
    """Enhanced pipeline with comprehensive error handling."""
    try:
        Logger.info(f"Starting pipeline for URL: {url}", {"dry_run": dry_run})

        # Validate URL
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        cfg = get_config(url)
        cfg.DRY_RUN = dry_run

        Logger.info(f"Initiating pipeline for: {url}")
        if cfg.DRY_RUN:
            Logger.dry_run("Mode active. No video will be downloaded or processed.")

        # Phase 1: Metadata and chat analysis (always runs)
        try:
            Logger.info("Phase 1: Downloading metadata and chat")
            ingester = ContentIngester(cfg.OUTPUT_DIR)
            platform = "twitch" if "twitch.tv" in url else "youtube"

            paths = ingester.download_chat_and_transcript(url, "test_video")

            if not paths or not paths.get("chat"):
                Logger.warning("No chat data available for analysis")
                return

            chat_df = parsers.parse_chat_log(paths["chat"], platform=platform)

            if chat_df.empty:
                Logger.warning("Chat parsing resulted in empty dataset")
                return

        except Exception as e:
            Logger.error("Failed during metadata and chat analysis phase", e)
            return

        # Phase 2: Analysis
        try:
            Logger.info("Phase 2: Analyzing chat signals")
            spike_seconds = process_chat_signals(
                chat_df, window_min=cfg.ROLLING_WINDOW_MIN
            )
            final_ranges = robust_merge_ranges(
                spike_seconds, cfg.PADDING_PRE_SEC, cfg.PADDING_POST_SEC
            )

            Logger.info(
                f"Analysis complete. Found {len(final_ranges)} highlight clusters."
            )

            if len(final_ranges) == 0:
                Logger.info("No highlights detected in stream")
                return

        except Exception as e:
            Logger.error("Failed during signal analysis phase", e)
            return

        # 3. DOWNLOAD PHASE
        raw_files = []
        video_id = cfg.OUTPUT_DIR.split("/")[-1]
        buffered_ranges = [
            (s - DOWNLOAD_BUFFER, e + DOWNLOAD_BUFFER) for s, e in final_ranges
        ]

        if not cfg.DRY_RUN:
            try:
                Logger.info(f"Downloading {len(buffered_ranges)} video segments")
                raw_files = ingester.download_specific_clips(
                    url, video_id, buffered_ranges
                )

                if not raw_files:
                    Logger.error("No video clips were successfully downloaded")
                    return

                Logger.success(f"Successfully downloaded {len(raw_files)} video clips")

            except Exception as e:
                Logger.error(
                    "Failed to download video clips",
                    e,
                    {"url": url, "segments": len(buffered_ranges)},
                )
                return

        # 4. PROCESSING LOOP
        Logger.info("Processing video clips for editor compatibility")
        processed_files = []

        for i, (start, end) in enumerate(final_ranges):
            duration = end - start
            Logger.info(f"Clip {i + 1}: {start}s to {end}s (Duration: {duration}s)")

            # --- DOWNLOAD STEP ---
            if cfg.DRY_RUN:
                Logger.dry_run(
                    f'yt-dlp --download-ranges "{start - DOWNLOAD_BUFFER}-{end + DOWNLOAD_BUFFER}" '
                    f'--format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" '
                    f'--force-keyframes-at-cuts --output "{video_id}_raw_clip_{i:03d}.%(ext)s" '
                    f"{url}",
                    {"segment": i + 1, "start": start, "end": end},
                )

            # --- TRANSCODE STEP ---
            if cfg.DRY_RUN:
                input_file = f"raw_clip_{i}.mp4"
                output_file = f"Highlight_{i}_Clean.mp4"
                Logger.dry_run(
                    f"ffmpeg -i {input_file} -r 60 -c:v libx264 -crf 18 -preset fast "
                    f"-c:a aac -ar 48000 -strict experimental {output_file}",
                    {"segment": i + 1, "input": input_file, "output": output_file},
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
                        success = normalize_clip(raw_path, final_path)

                        if success:
                            Logger.success(f"✓ Saved: {final_filename}")
                            processed_files.append(final_path)
                        else:
                            Logger.error(f"✗ Failed to normalize: {raw_path}")
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

            except Exception as e:
                Logger.error(
                    "Failed to generate EDL",
                    e,
                    {
                        "video_path": video_path if video_path else "N/A",
                        "edl_path": edl_path if edl_path else "N/A",
                    },
                )
        elif cfg.DRY_RUN:
            video_id = cfg.OUTPUT_DIR.split("/")[-1]
            Logger.dry_run(
                f"EDL generation would create: {video_id}.edl with {len(final_ranges)} clips"
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

    args = parser.parse_args()

    run_clip_generator(args.url, dry_run=args.dry_run)
