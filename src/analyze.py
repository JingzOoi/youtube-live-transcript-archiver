import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from scipy.stats import median_abs_deviation
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import List, Tuple, Dict, Any


def detect_mad_peaks(
    counts: np.ndarray, threshold_multiplier: float = 1.0
) -> Tuple[np.ndarray, float]:
    """
    Detects peaks using Median Absolute Deviation (MAD).
    """
    baseline = np.median(counts)
    mad = median_abs_deviation(counts)
    if mad == 0:
        mad = 1  # Prevent division by zero

    threshold = baseline + (mad * threshold_multiplier)
    peaks, _ = find_peaks(counts, height=threshold)
    return peaks, threshold


def calculate_highlight_scores(
    metrics: pd.DataFrame, activity_weight: float = 0.7, sentiment_weight: float = 0.3
) -> pd.DataFrame:
    """
    Calculates normalized highlight scores based on activity and sentiment.
    """

    def normalize(series):
        if series.max() == series.min():
            return series * 0
        return (series - series.min()) / (series.max() - series.min())

    metrics["norm_count"] = normalize(metrics["message_count"])
    metrics["norm_sent"] = normalize(metrics["avg_sentiment"])

    metrics["highlight_score"] = (activity_weight * metrics["norm_count"]) + (
        sentiment_weight * metrics["norm_sent"]
    )
    return metrics


def get_dynamic_segments(
    peaks: List[int],
    chat_df: pd.DataFrame,
    baseline_median: float,
    buildup_window: int = 10,
    winddown_window: int = 15,
    min_pre_padding: int = 180,
    min_post_padding: int = 120,
    activity_multiplier: float = 1.5,
    drop_off_confirm_mins: int = 2,
) -> List[Tuple[int, int]]:
    """
    Intelligently expands highlight boundaries based on chat density.
    """
    segments = []
    min_min = int(chat_df["minute"].min())
    max_min = int(chat_df["minute"].max())

    counts_series = (
        chat_df.groupby("minute").size().reindex(range(min_min, max_min + 1), fill_value=0)
    )
    activity_threshold = baseline_median * activity_multiplier

    for peak_min in sorted(peaks):
        peak_sec = peak_min * 60

        # --- 1. Find Start (Ramp-Up) ---
        start_min = peak_min
        search_start = max(min_min, peak_min - buildup_window)

        for m in range(peak_min - 1, search_start - 1, -1):
            if counts_series.get(m, 0) < activity_threshold:
                start_min = m
                break
            start_min = m

        dynamic_start_sec = start_min * 60
        safe_start_sec = peak_sec - min_pre_padding
        final_start_sec = max(min_min * 60, min(dynamic_start_sec, safe_start_sec))

        # --- 2. Find End (Drop-Off) ---
        end_min = peak_min
        search_end = min(max_min, peak_min + winddown_window)
        quiet_streak = 0

        for m in range(peak_min + 1, search_end + 1):
            if counts_series.get(m, 0) < activity_threshold:
                quiet_streak += 1
            else:
                quiet_streak = 0

            if quiet_streak >= drop_off_confirm_mins:
                end_min = m - quiet_streak + 1
                break
            end_min = m

        dynamic_end_sec = (end_min + 1) * 60
        safe_end_sec = peak_sec + min_post_padding
        final_end_sec = max(dynamic_end_sec, safe_end_sec)

        segments.append((int(final_start_sec), int(final_end_sec)))

    return segments


def merge_segments(segments: List[Tuple[int, int]], gap_threshold: int = 10) -> List[Tuple[int, int]]:
    """
    Merges overlapping or nearby time segments.
    """
    if not segments:
        return []
    segments.sort(key=lambda x: x[0])
    merged = []
    current_start, current_end = segments[0]

    for next_start, next_end in segments[1:]:
        if next_start <= current_end + gap_threshold:
            current_end = max(current_end, next_end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = next_start, next_end

    merged.append((current_start, current_end))
    return merged


def process_chat_signals(
    chat_df: pd.DataFrame,
    activity_weight: float = 0.7,
    sentiment_weight: float = 0.3,
    threshold_multiplier: float = 1.5,
) -> List[Tuple[int, int]]:
    """
    Full pipeline: Sentiment -> Metrics -> Highlight Scoring -> Peak Detection -> Dynamic Padding.
    """
    if chat_df.empty:
        return []

    # 1. Sentiment Scoring
    analyzer = SentimentIntensityAnalyzer()
    unique_msgs = chat_df["message"].astype(str).unique()
    scores = {msg: analyzer.polarity_scores(msg)["compound"] for msg in unique_msgs}
    chat_df["sentiment"] = chat_df["message"].map(scores)

    # 2. Aggregate by minute
    metrics = (
        chat_df.groupby("minute")
        .agg(message_count=("message", "size"), avg_sentiment=("sentiment", "mean"))
        .reset_index()
    )

    # 3. Calculate Highlight Scores
    metrics = calculate_highlight_scores(metrics, activity_weight, sentiment_weight)

    # 4. Detect Highlight Peaks
    peaks, _ = detect_mad_peaks(metrics["highlight_score"].values, threshold_multiplier)
    highlight_minutes = metrics.loc[peaks, "minute"].tolist()

    if not highlight_minutes:
        return []

    # 5. Dynamic Padding
    baseline_median = metrics["message_count"].median()
    raw_segments = get_dynamic_segments(highlight_minutes, chat_df, baseline_median)
    
    # 6. Merge
    final_segments = merge_segments(raw_segments)

    return final_segments
