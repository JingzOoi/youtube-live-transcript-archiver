# -*- coding: utf-8 -*-
"""
Integration tests for YouTube/Twitch Live Clip Generator.
Run with `python -m unittest tests_integration.py`
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
from pathlib import Path

# Import modules to test
from main import run_clip_generator
from src.ingest import ContentIngester
from src.analyze import process_chat_signals
from src.video import get_video_metadata, normalize_clip
from src.export import generate_professional_edl
from src import parsers
from src.utils import Logger
from config import get_config


class BaseIntegrationTest(unittest.TestCase):
    """Base class with common mock setup and teardown."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_url = "https://www.youtube.com/watch?v=test123"
        self.test_video_id = "test123"

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_mock_config(self):
        """Create mock configuration for testing."""
        return get_config(self.test_url)

    def create_sample_chat_data(self):
        """Create sample chat DataFrame for testing."""
        # Create data with clear activity spikes
        base_data = []
        # Low activity period
        for i in range(0, 600, 30):  # Every 30 seconds for 10 minutes
            base_data.append([i, f"message_{i}", f"user_{i}"])
        # High activity spike at 10 minutes (600 seconds)
        for i in range(600, 660, 5):  # Every 5 seconds for 1 minute
            base_data.append([i, f"exciting_message_{i}!", f"user_{i}"])
        # Low activity again
        for i in range(660, 1200, 30):  # Every 30 seconds for 9 minutes
            base_data.append([i, f"message_{i}", f"user_{i}"])
        # Another spike at 20 minutes (1200 seconds)
        for i in range(1200, 1260, 5):  # Every 5 seconds for 1 minute
            base_data.append([i, f"amazing_message_{i}!", f"user_{i}"])

        return pd.DataFrame(
            base_data, columns=["offset_seconds", "message", "author_name"]
        )

    def create_sample_chat_json(self):
        """Create sample YouTube chat JSON for testing."""
        return [
            '{"replayChatItemAction":{"videoOffsetTimeMsec":"10000","actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"authorName":{"simpleText":"user1"},"message":{"runs":[{"text":"hello"}]},"timestampUsec":"10000000"}}}]}}',
            '{"replayChatItemAction":{"videoOffsetTimeMsec":"120000","actions":[{"addChatItemAction":{"item":{"liveChatTextMessageRenderer":{"authorName":{"simpleText":"user2"},"message":{"runs":[{"text":"exciting!"}]},"timestampUsec":"120000000"}}}]}}',
        ]


class TestEndToEndPipeline(BaseIntegrationTest):
    """Test complete pipeline functionality."""

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    @patch("src.parsers.parse_chat_log")
    @patch("main.process_chat_signals")
    @patch("src.ingest.ContentIngester.download_specific_clips")
    @patch("src.video.normalize_clip")
    @patch("src.video.get_video_metadata")
    @patch("src.export.generate_professional_edl")
    def test_youtube_pipeline_dry_run(
        self,
        mock_edl,
        mock_metadata,
        mock_normalize,
        mock_download,
        mock_signals,
        mock_parse,
        mock_chat,
    ):
        """Test complete YouTube pipeline in dry-run mode."""
        # Setup mocks
        mock_chat.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = [120, 130]  # Spike times
        mock_download.return_value = []  # No downloads in dry run

        # Run pipeline
        run_clip_generator(self.test_url, dry_run=True)

        # Verify mocks were called correctly
        mock_chat.assert_called_once()
        mock_parse.assert_called_once()
        mock_signals.assert_called_once()
        mock_download.assert_not_called()  # Should not download in dry run
        mock_normalize.assert_not_called()  # Should not normalize in dry run
        mock_metadata.assert_not_called()  # Should not probe metadata in dry run
        mock_edl.assert_not_called()  # Should not generate EDL in dry run

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    @patch("src.parsers.parse_chat_log")
    @patch("main.process_chat_signals")
    @patch("src.ingest.ContentIngester.download_specific_clips")
    @patch("src.video.normalize_clip")
    @patch("src.video.get_video_metadata")
    @patch("src.export.generate_professional_edl")
    def test_youtube_pipeline_full_execution(
        self,
        mock_edl,
        mock_metadata,
        mock_normalize,
        mock_download,
        mock_signals,
        mock_parse,
        mock_chat,
    ):
        """Test complete YouTube pipeline with actual processing."""
        # Setup mocks
        mock_chat.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = [120, 130]
        mock_download.return_value = [Path("/tmp/clip1.mp4"), Path("/tmp/clip2.mp4")]
        mock_normalize.return_value = True
        mock_metadata.return_value = {"fps": 30.0, "duration": 3600}

        # Run pipeline
        run_clip_generator(self.test_url, dry_run=False)

        # Verify all components were called
        mock_chat.assert_called_once()
        mock_parse.assert_called_once()
        mock_signals.assert_called_once()
        mock_download.assert_called_once()
        self.assertEqual(mock_normalize.call_count, 2)  # Two clips
        mock_metadata.assert_called_once()
        mock_edl.assert_called_once()

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    @patch("src.parsers.parse_chat_log")
    @patch("main.process_chat_signals")
    def test_pipeline_no_highlights_detected(self, mock_signals, mock_parse, mock_chat):
        """Test pipeline behavior when no highlights are detected."""
        # Setup mocks
        mock_chat.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = []  # No spikes detected

        # Run pipeline
        run_clip_generator(self.test_url, dry_run=True)

        # Verify pipeline completed but indicated no highlights
        mock_chat.assert_called_once()
        mock_parse.assert_called_once()
        mock_signals.assert_called_once()


class TestErrorHandlingIntegration(BaseIntegrationTest):
    """Test error handling and recovery scenarios."""

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    def test_network_failure_handling(self, mock_download):
        """Test handling of network failures during ingestion."""
        mock_download.side_effect = Exception("Network error")

        # Should handle error gracefully and not crash
        run_clip_generator(self.test_url, dry_run=True)

        # Verify error was logged (would need to capture stdout in real test)
        mock_download.assert_called_once()

    @patch("src.parsers.parse_chat_log")
    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    def test_empty_chat_handling(self, mock_download, mock_parse):
        """Test handling of empty or invalid chat data."""
        mock_download.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = pd.DataFrame()  # Empty DataFrame

        # Should handle empty data gracefully
        run_clip_generator(self.test_url, dry_run=True)

        mock_download.assert_called_once()
        mock_parse.assert_called_once()

    @patch("main.process_chat_signals")
    @patch("src.parsers.parse_chat_log")
    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    def test_analysis_failure_handling(self, mock_download, mock_parse, mock_signals):
        """Test handling of analysis phase failures."""
        mock_download.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.side_effect = Exception("Analysis failed")

        # Should handle analysis error gracefully
        run_clip_generator(self.test_url, dry_run=True)

        mock_download.assert_called_once()
        mock_parse.assert_called_once()
        mock_signals.assert_called_once()

    def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        invalid_urls = ["", None, "not-a-url", "ftp://invalid.com"]

        for url in invalid_urls:
            with self.assertRaises(SystemExit):
                run_clip_generator(url, dry_run=True)


class TestComponentIntegration(BaseIntegrationTest):
    """Test integration between specific components."""

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    def test_ingest_parser_integration(self, mock_download):
        """Test integration between ingestion and parsing."""
        # Create temporary chat file
        chat_file = os.path.join(self.test_dir, "test_chat.json")
        with open(chat_file, "w") as f:
            f.write("\n".join(self.create_sample_chat_json()))

        mock_download.return_value = {"chat": chat_file}

        # Test that parsing works with real downloaded data
        run_clip_generator(self.test_url, dry_run=True)

        mock_download.assert_called_once()

    @patch("main.process_chat_signals")
    @patch("src.parsers.parse_chat_log")
    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    def test_analysis_download_integration(
        self, mock_download, mock_parse, mock_signals
    ):
        """Test integration between analysis and download phases."""
        mock_download.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = [60, 120, 180]  # Three spikes

        # Run pipeline and verify integration
        run_clip_generator(self.test_url, dry_run=True)

        # Verify that analysis results would be used for download ranges
        mock_download.assert_called_once()
        mock_parse.assert_called_once()
        mock_signals.assert_called_once()


class TestLoggerFunctionality(BaseIntegrationTest):
    """Test enhanced Logger class."""

    @patch("builtins.print")
    def test_error_logging_with_exception(self, mock_print):
        """Test error logging with exception details."""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            Logger.error("Test error message", e, {"context": "test"})

            # Verify print was called with error message and exception details
            mock_print.assert_called()
            call_args = str(mock_print.call_args)
            self.assertIn("[ERROR]", call_args)
            self.assertIn("Test error message", call_args)
            self.assertIn("ValueError", call_args)
            self.assertIn("Test exception", call_args)

    @patch("builtins.print")
    def test_progress_logging(self, mock_print):
        """Test progress logging functionality."""
        Logger.progress("Downloading", 5, 10, "video.mp4")

        # Verify progress message format
        mock_print.assert_called_once()
        call_args = str(mock_print.call_args)
        self.assertIn("[PROGRESS]", call_args)
        self.assertIn("Downloading: 5/10 (50.0%)", call_args)
        self.assertIn("video.mp4", call_args)


class TestPlatformDetection(BaseIntegrationTest):
    """Test platform detection and handling."""

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    @patch("src.parsers.parse_chat_log")
    @patch("main.process_chat_signals")
    def test_youtube_platform_detection(self, mock_signals, mock_parse, mock_download):
        """Test YouTube platform detection."""
        youtube_url = "https://www.youtube.com/watch?v=test123"
        mock_download.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = []

        run_clip_generator(youtube_url, dry_run=True)

        # Verify YouTube platform was detected
        mock_parse.assert_called_once()
        parse_call_args = mock_parse.call_args[0]
        self.assertEqual(parse_call_args[1], "youtube")  # platform parameter

    @patch("src.ingest.ContentIngester.download_chat_and_transcript")
    @patch("src.parsers.parse_chat_log")
    @patch("main.process_chat_signals")
    def test_twitch_platform_detection(self, mock_signals, mock_parse, mock_download):
        """Test Twitch platform detection."""
        twitch_url = "https://www.twitch.tv/videos/123456"
        mock_download.return_value = {"chat": "/tmp/test_chat.json"}
        mock_parse.return_value = self.create_sample_chat_data()
        mock_signals.return_value = []

        run_clip_generator(twitch_url, dry_run=True)

        # Verify Twitch platform was detected
        mock_parse.assert_called_once()
        parse_call_args = mock_parse.call_args[0]
        self.assertEqual(parse_call_args[1], "twitch")  # platform parameter


if __name__ == "__main__":
    unittest.main()
