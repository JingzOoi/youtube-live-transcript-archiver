# -*- coding: utf-8 -*-
"""
Common test configuration and fixtures for YouTube Live Transcript Archiver.
"""

import unittest
import tempfile
import os
import pandas as pd
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
import sys

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import get_config


class TestConfig:
    """Test configuration constants."""

    SAMPLE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    SAMPLE_VIDEO_ID = "dQw4w9WgXcQ"

    # Time slices for testing
    START_TIME_30S = 30
    END_TIME_2MIN = 120
    TIME_SLICE_1MIN = (60, 120)  # 1-2 minutes
    TIME_SLICE_2MIN = (180, 300)  # 3-5 minutes

    # Test data paths
    FIXTURES_DIR = Path(__file__).parent
    SAMPLE_VTT = FIXTURES_DIR / "sample_transcript.vtt"
    SAMPLE_CHAT_JSON = FIXTURES_DIR / "sample_chat.json"


def create_sample_vtt():
    """Create sample VTT file content."""
    return """WEBVTT

00:00:10.000 --> 00:00:15.000
First segment

00:01:30.000 --> 00:01:35.000
Second segment

00:02:45.000 --> 00:02:50.000
Third segment
"""


def create_sample_chat_json():
    """Create sample chat JSON content."""
    return """{"replayChatItemAction":{"videoOffsetTimeMsec":"5000","actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"authorName":{"simpleText":"TestUser"},"message":{"runs":[{"text":"Hello world"}]},"timestampUsec":"5000000"}}}}]}}"""


def create_sample_transcript_df():
    """Provide sample transcript DataFrame."""
    return pd.DataFrame(
        {
            "start_time": ["00:00:10.000", "00:01:30.000", "00:02:45.000"],
            "end_time": ["00:00:15.000", "00:01:35.000", "00:02:50.000"],
            "offset_start_seconds": [10.0, 90.0, 165.0],
            "offset_end_seconds": [15.0, 95.0, 170.0],
            "text": ["First segment", "Second segment", "Third segment"],
        }
    )


def create_sample_chat_df():
    """Provide sample chat DataFrame."""
    return pd.DataFrame(
        {
            "offset_seconds": [5, 15, 25, 35, 45],
            "message": ["hello", "world", "test message", "lmao", "wow"],
            "author_name": ["user1", "user2", "user3", "user4", "user5"],
        }
    )


def create_sample_analysis_data():
    """Provide sample analysis data for report testing."""
    return {
        "highlights": [(30.0, 60.0), (120.0, 150.0)],
        "spike_seconds": [35.0, 125.0],
        "chat_df": create_sample_chat_df(),
        "transcript_df": create_sample_transcript_df(),
    }


def assert_dataframes_equal(df1, df2):
    """Assert that two DataFrames are equal, handling NaN values."""
    pd.testing.assert_frame_equal(df1, df2, check_dtype=False, check_exact=False)


def assert_valid_highlight_ranges(ranges):
    """Assert that highlight ranges are valid."""
    assert isinstance(ranges, list)
    for start, end in ranges:
        assert isinstance(start, (int, float))
        assert isinstance(end, (int, float))
        assert start < end
        assert start >= 0
        assert end > 0
