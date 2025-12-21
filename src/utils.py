import sys
import os
import json
import datetime
import pandas as pd
from typing import Optional, Any, Dict, List


class Logger:
    """Enhanced logging utility with multiple severity levels and structured output."""

    @classmethod
    def info(cls, msg: str, context: Optional[dict] = None):
        """General information messages."""
        formatted_msg = f"[INFO] {msg}"
        if context:
            formatted_msg += f" | Context: {context}"
        print(formatted_msg)

    @classmethod
    def error(
        cls,
        msg: str,
        exception: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        """Critical errors that stop execution."""
        error_msg = f"\033[91m[ERROR]\033[0m {msg}"
        if exception:
            error_msg += f" | Exception: {type(exception).__name__}: {str(exception)}"
        if context:
            error_msg += f" | Context: {context}"
        print(error_msg)

    @classmethod
    def warning(cls, msg: str, context: Optional[dict] = None):
        """Recoverable issues or potential problems."""
        warning_msg = f"\033[93m[WARNING]\033[0m {msg}"
        if context:
            warning_msg += f" | Context: {context}"
        print(warning_msg)

    @classmethod
    def debug(cls, msg: str, context: Optional[dict] = None):
        """Detailed debugging information."""
        debug_msg = f"[DEBUG] {msg}"
        if context:
            debug_msg += f" | Context: {context}"
        print(debug_msg)

    @classmethod
    def success(cls, msg: str, context: Optional[dict] = None):
        """Successful operation completion."""
        success_msg = f"\033[92m[SUCCESS]\033[0m {msg}"
        if context:
            success_msg += f" | Context: {context}"
        print(success_msg)

    @classmethod
    def dry_run(cls, msg: str, context: Optional[dict] = None):
        """Dry run simulation messages."""
        dry_msg = f"\033[93m[DRY RUN - SIMULATION]\033[0m {msg}"
        if context:
            dry_msg += f" | Context: {context}"
        print(dry_msg)

    @classmethod
    def progress(
        cls, operation: str, current: int, total: int, item: Optional[str] = None
    ):
        """Progress tracking for long-running operations."""
        percentage = (current / total) * 100 if total > 0 else 0
        msg = f"{operation}: {current}/{total} ({percentage:.1f}%)"
        if item:
            msg += f" - {item}"
        print(f"[PROGRESS] {msg}")


class AnalysisReporter:
    """Enhanced logging utility that saves detailed analysis reports to files."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.analysis_log = {
            "run_info": {},
            "configuration": {},
            "data_summary": {},
            "analysis_results": {},
            "processing_steps": [],
            "highlights": [],
            "transcript_contexts": [],
            "errors": [],
            "commands_run": [],
            "performance_metrics": {},
        }

    def start_run(self, url: str, dry_run: bool = False):
        """Initialize a new analysis run."""
        self.analysis_log["run_info"] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "url": url,
            "dry_run": dry_run,
            "version": "1.0.0",
        }

    def log_configuration(self, config: Dict[str, Any]):
        """Log the configuration used for this run."""
        self.analysis_log["configuration"] = config

    def log_data_summary(
        self, chat_df: pd.DataFrame, transcript_df: Optional[pd.DataFrame] = None
    ):
        """Log summary of loaded data."""
        self.analysis_log["data_summary"] = {
            "chat_messages": len(chat_df),
            "chat_time_range": f"{chat_df['offset_seconds'].min():.1f}s - {chat_df['offset_seconds'].max():.1f}s"
            if not chat_df.empty
            else "N/A",
            "transcript_segments": len(transcript_df)
            if transcript_df is not None
            else 0,
            "transcript_time_range": f"{transcript_df['offset_start_seconds'].min():.1f}s - {transcript_df['offset_end_seconds'].max():.1f}s"
            if transcript_df is not None and not transcript_df.empty
            else "N/A",
        }

    def log_processing_step(
        self, step_name: str, details: Optional[Dict[str, Any]] = None
    ):
        """Log a processing step with details."""
        step_entry = {
            "step": step_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details or {},
        }
        self.analysis_log["processing_steps"].append(step_entry)

    def log_highlights(
        self,
        highlight_ranges: List[tuple],
        spike_seconds: List[float],
        trigger_info: Optional[List[Dict]] = None,
    ):
        """Log detected highlights with context."""
        highlights = []
        for i, (start, end) in enumerate(highlight_ranges):
            highlight_info = {
                "id": i + 1,
                "start_seconds": start,
                "end_seconds": end,
                "duration": end - start,
                "original_spike_time": spike_seconds[i]
                if i < len(spike_seconds)
                else None,
            }
            if trigger_info and i < len(trigger_info):
                highlight_info.update(trigger_info[i])
            highlights.append(highlight_info)
        self.analysis_log["highlights"] = highlights

    def log_transcript_context(
        self,
        highlight_id: int,
        start_time: float,
        end_time: float,
        transcript_df: pd.DataFrame,
    ):
        """Log transcript context for a highlight."""
        if transcript_df.empty:
            return

        # Import here to avoid circular imports
        from .parsers import get_transcript_segment

        segment = get_transcript_segment(transcript_df, start_time, end_time)
        if not segment.empty:
            context = {
                "highlight_id": highlight_id,
                "time_range": f"{start_time:.1f}s - {end_time:.1f}s",
                "transcript_segments": len(segment),
                "text_content": segment["text"].tolist(),
            }
            self.analysis_log["transcript_contexts"].append(context)

    def log_command(self, command: str, purpose: str, success: bool = True):
        """Log a command that was executed."""
        cmd_entry = {
            "command": command,
            "purpose": purpose,
            "timestamp": datetime.datetime.now().isoformat(),
            "success": success,
        }
        self.analysis_log["commands_run"].append(cmd_entry)

    def log_error(
        self,
        error_msg: str,
        exception: Optional[Exception] = None,
        context: Optional[Dict] = None,
    ):
        """Log an error that occurred."""
        error_entry = {
            "error": error_msg,
            "exception": str(exception) if exception else None,
            "context": context or {},
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.analysis_log["errors"].append(error_entry)

    def save_report(self, filename: Optional[str] = None):
        """Save the analysis report to a JSON file."""
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_report_{timestamp}.json"

        report_path = os.path.join(self.output_dir, filename)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.analysis_log, f, indent=2, ensure_ascii=False)

        return report_path

def extract_transcript_by_minutes(transcript_df: pd.DataFrame, minutes: Any) -> Dict[int, str]:
    """
    Retrieves subtitle text for specific minutes from a transcript DataFrame.
    """
    if isinstance(minutes, (int, float)):
        minutes = [int(minutes)]

    results = {}
    for m in minutes:
        start_sec = m * 60
        end_sec = (m + 1) * 60

        mask = (transcript_df["offset_start_seconds"] >= start_sec) & (
            transcript_df["offset_start_seconds"] < end_sec
        )

        segment = transcript_df[mask]
        if not segment.empty:
            text = " ".join(segment["text"].tolist())
            results[m] = text.strip()
        else:
            results[m] = "(No speech detected)"

    return results


def convert_time(seconds: float, format_type: str = "readable", fps: int = 60) -> str:
    """
    Unified time conversion utility.
    Formats: 'timecode' (HH:MM:SS:FF) or 'readable' (HH:MM:SS or MM:SS)
    """
    if format_type == "timecode":
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * fps)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
    elif format_type == "readable":
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    else:
        raise ValueError(f"Unknown format_type: {format_type}")


def get_seconds_from_tuple(tup: Optional[tuple]) -> int:
    """Helper to convert (H, M, S) tuple to total seconds."""
    if not tup:
        return 0
    return tup[0] * 3600 + tup[1] * 60 + tup[2]
