# -*- coding: utf-8 -*-
"""
Unit tests for parsers module.
Run with `python -m unittest tests.unit.test_parsers`
"""

import unittest
import tempfile
import pandas as pd
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src import parsers
from config import get_config


class TestParsers(unittest.TestCase):
    """Test parser functionality."""

    def test_parse_transcript_vtt(self):
        """Test VTT transcript parsing."""
        # Create temporary VTT file
        vtt_content = """WEBVTT

00:00:10.000 --> 00:00:15.000
First segment

00:01:30.000 --> 00:01:35.000
Second segment

00:02:45.000 --> 00:02:50.000
Third segment
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8", suffix=".vtt"
        ) as tmp:
            tmp.write(vtt_content)
            tmp_path = tmp.name

        try:
            result_df = parsers.parse_transcript_vtt(tmp_path)
            self.assertIsInstance(result_df, pd.DataFrame)
            self.assertEqual(len(result_df), 3)
            self.assertIn("start_time", result_df.columns)
            self.assertIn("end_time", result_df.columns)
            self.assertIn("text", result_df.columns)
            self.assertIn("offset_start_seconds", result_df.columns)

            # Check first entry
            first_row = result_df.iloc[0]
            self.assertEqual(first_row["start_time"], "00:00:10.000")
            self.assertEqual(first_row["text"], "First segment")
            self.assertEqual(first_row["offset_start_seconds"], 10.0)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_parse_chat_log_youtube(self):
        """Test YouTube chat log parsing."""
        # Create temporary chat file
        chat_content = """{"replayChatItemAction":{"videoOffsetTimeMsec":"5000","actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"authorName":{"simpleText":"TestUser"},"message":{"runs":[{"text":"Hello world"}]},"timestampUsec":"5000000"}}}}]}}\n"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8", suffix=".json"
        ) as tmp:
            tmp.write(chat_content)
            tmp_path = tmp.name

        try:
            result_df = parsers.parse_chat_log(tmp_path, "youtube")
            self.assertIsInstance(result_df, pd.DataFrame)
            self.assertEqual(len(result_df), 1)
            self.assertIn("offset_seconds", result_df.columns)
            self.assertIn("message", result_df.columns)
            self.assertIn("author_name", result_df.columns)

            # Check entry content
            first_row = result_df.iloc[0]
            self.assertEqual(first_row["offset_seconds"], 5.0)
            self.assertEqual(first_row["message"], "Hello world")
            self.assertEqual(first_row["author_name"], "TestUser")
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_transcript_segment(self):
        """Test transcript segment retrieval."""
        # Create sample transcript data
        test_transcript = pd.DataFrame(
            {
                "start_time": ["00:00:10.000", "00:01:30.000", "00:02:45.000"],
                "end_time": ["00:00:15.000", "00:01:35.000", "00:02:50.000"],
                "offset_start_seconds": [10.0, 90.0, 165.0],
                "offset_end_seconds": [15.0, 95.0, 170.0],
                "text": ["First segment", "Second segment", "Third segment"],
            }
        )

        # Test full transcript (no time bounds)
        full_transcript = parsers.get_transcript_segment(test_transcript)
        self.assertEqual(len(full_transcript), 3)

        # Test time-sliced transcript (60-180 seconds)
        sliced_transcript = parsers.get_transcript_segment(test_transcript, 60.0, 180.0)
        self.assertEqual(len(sliced_transcript), 2)
        self.assertIn("Second segment", sliced_transcript["text"].tolist())
        self.assertIn("Third segment", sliced_transcript["text"].tolist())

        # Test start-only slice
        start_only = parsers.get_transcript_segment(test_transcript, start_time=100.0)
        self.assertEqual(len(start_only), 1)  # Last two segments

        # Test end-only slice
        end_only = parsers.get_transcript_segment(test_transcript, end_time=50.0)
        self.assertEqual(len(end_only), 1)  # First segment only

    def test_apply_text_replacements(self):
        """Test text replacement functionality."""
        text = "Hello cleo, welcome to FaZe clan! &gt;Hello&lt;"
        replacements = [
            ("cleo", "clio"),
            ("FaZe", "Phase"),
            ("&gt;", ">"),
            ("&lt;", "<"),
        ]

        result_text, stats = parsers.apply_text_replacements(text, replacements)

        expected = "Hello clio, welcome to Phase clan! >Hello<"
        self.assertEqual(result_text, expected)

        # Check replacement statistics
        self.assertEqual(stats["cleo"]["count"], 1)
        self.assertEqual(stats["cleo"]["replacement"], "clio")
        self.assertEqual(stats["FaZe"]["count"], 1)
        self.assertEqual(stats["FaZe"]["replacement"], "Phase")


if __name__ == "__main__":
    unittest.main()
