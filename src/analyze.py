import pandas as pd
import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def process_chat_signals(
    chat_df: pd.DataFrame, time_col="offset_seconds", bucket_size_sec=15, window_min=20
):
    """
    Advanced Signal Processing:
    1. Buckets data into 15s chunks (High Res).
    2. Calculates Rolling Z-Score (Adaptive Threshold).
    3. Merges Sentiment.
    """
    if chat_df.empty:
        return []

    # 1. Bucketize
    chat_df["bucket"] = (chat_df[time_col] // bucket_size_sec).astype(int)

    # 2. Vectorized Sentiment (Faster than .apply)
    analyzer = SentimentIntensityAnalyzer()
    # Optimization: Extract only unique messages to score, then map back
    unique_msgs = chat_df["message"].astype(str).unique()
    scores = {msg: analyzer.polarity_scores(msg)["compound"] for msg in unique_msgs}
    chat_df["sentiment"] = chat_df["message"].map(scores)

    # 3. Aggregate
    timeline = (
        chat_df.groupby("bucket")
        .agg(msg_count=("message", "count"), avg_sentiment=("sentiment", "mean"))
        .reindex(range(int(chat_df["bucket"].max()) + 1), fill_value=0)
    )

    # Ensure timeline is a DataFrame and reset index to make bucket a column
    timeline = timeline.reset_index()

    # 4. Rolling Statistics (The "A+" upgrade)
    # Window size in buckets (e.g., 20 mins * 4 buckets/min = 80 buckets)
    roll_window = int((window_min * 60) / bucket_size_sec)

    timeline["rolling_mean"] = (
        timeline["msg_count"].rolling(window=roll_window, min_periods=10).mean()
    )
    timeline["rolling_std"] = (
        timeline["msg_count"].rolling(window=roll_window, min_periods=10).std()
    )

    # Avoid division by zero
    timeline["rolling_std"] = timeline["rolling_std"].fillna(0).replace(0, 1)

    # Calculate Z-Score: (Value - Mean) / StdDev
    timeline["z_score"] = (timeline["msg_count"] - timeline["rolling_mean"]) / timeline[
        "rolling_std"
    ]

    # 5. Detect Spikes (Z-Score > 3.0 implies 99.7% outlier probability)
    spikes = timeline[timeline["z_score"] > 3.0].copy()

    # Return raw seconds for highlights
    return list(spikes.index * bucket_size_sec)
