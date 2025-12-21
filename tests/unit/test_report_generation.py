# -*- coding: utf-8 -*-
"""
Test utilities for report generation system.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.reporting import HTMLReporter, OptimizedJSONReporter, ReportGenerator


class TestReportGeneration(unittest.TestCase):
    """Test report generation functionality."""

    def setUp(self):
        """Create temporary output directory for tests."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_reports_")
        self.addCleanup(lambda: os.system(f"rm -rf {self.temp_dir}"))

    def test_html_report_generation(self):
        """Test HTML report generation."""
        from config import AppConfig

        # Test configuration
        config = {
            "REPORT_FORMAT": "html",
            "INCLUDE_TRANSCRIPT_CONTEXT": True,
            "HTML_INCLUDE_CHARTS": True,
            "MAX_TRANSCRIPT_EXCERPT": 100,
            "REPLACE_WORDS": [("test", "TEST"), ("url", "[URL]")],
        }

        # Sample analysis data
        analysis_data = {
            "run_info": {
                "url": "https://example.com/video",
                "timestamp": "2025-12-15T23:26:44Z",
                "dry_run": True,
            },
            "highlights": [
                {
                    "id": 1,
                    "start_seconds": 60.0,
                    "duration": 30.0,
                    "transcript_excerpt": "This is a test highlight",
                }
            ],
            "data_summary": {"chat_messages": 100, "transcript_segments": 50},
            "text_replacements_applied": {"test": {"count": 2, "replacement": "TEST"}},
        }

        # Generate report
        reporter = ReportGenerator(self.temp_dir, config)
        generated_files = reporter.generate_reports(analysis_data)

        # Verify HTML report was created
        self.assertEqual(len(generated_files), 1)
        self.assertTrue(os.path.exists(generated_files[0]))

        # Check HTML content
        with open(generated_files[0], "r", encoding="utf-8") as f:
            html_content = f.read()

        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("Stream Analysis Report", html_content)
        self.assertIn("Executive Summary", html_content)
        self.assertIn("Highlights", html_content)
        self.assertIn("Configuration", html_content)
        self.assertIn("Highlight Timeline", html_content)
        self.assertIn("Search", html_content)

    def test_json_report_generation(self):
        """Test JSON report generation."""
        from config import AppConfig

        # Test configuration
        config = {
            "REPORT_FORMAT": "json",
            "REPORT_COMPRESS_JSON": True,
            "INCLUDE_TRANSCRIPT_CONTEXT": False,
            "REPLACE_WORDS": [("test", "TEST")],
        }

        # Sample analysis data
        analysis_data = {
            "run_info": {"url": "test_url"},
            "highlights": [{"id": 1, "start_seconds": 60.0, "duration": 30.0}],
            "data_summary": {"chat_messages": 50},
        }

        # Generate report
        reporter = ReportGenerator(self.temp_dir, config)
        generated_files = reporter.generate_reports(analysis_data)

        # Verify JSON report was created and compressed
        self.assertEqual(len(generated_files), 1)
        self.assertTrue(os.path.exists(generated_files[0]))

        # Verify file extension
        self.assertTrue(generated_files[0].endswith(".json.gz"))

    def test_text_report_generation(self):
        """Test text report generation."""
        from config import AppConfig

        config = {"REPORT_FORMAT": "txt"}
        analysis_data = {
            "run_info": {"url": "test_url"},
            "highlights": [{"id": 1, "start_seconds": 60.0}],
            "data_summary": {"chat_messages": 25},
        }

        reporter = ReportGenerator(self.temp_dir, config)
        generated_files = reporter.generate_reports(analysis_data)

        self.assertEqual(len(generated_files), 1)
        self.assertTrue(os.path.exists(generated_files[0]))

        # Verify text content
        with open(generated_files[0], "r", encoding="utf-8") as f:
            text_content = f.read()

        self.assertIn("STREAM ANALYSIS REPORT", text_content)
        self.assertIn("Total Highlights: 1", text_content)
        self.assertIn("EXECUTIVE SUMMARY", text_content)
        self.assertIn("HIGHLIGHTS", text_content)

    def test_multiple_formats(self):
        """Test multiple report formats."""
        from config import AppConfig

        config = {"REPORT_FORMAT": "html,json,txt"}
        analysis_data = {
            "run_info": {"url": "test_url"},
            "highlights": [{"id": 1, "start_seconds": 60.0}],
            "data_summary": {"chat_messages": 50},
        }

        reporter = ReportGenerator(self.temp_dir, config)
        generated_files = reporter.generate_reports(analysis_data)

        # Should generate all three formats
        self.assertEqual(len(generated_files), 3)

        for file_path in generated_files:
            self.assertTrue(os.path.exists(file_path))

        # Verify file types
        file_extensions = [os.path.splitext(f)[1] for f in generated_files]
        self.assertIn(".html", file_extensions)
        # JSON files may be compressed (.json.gz)
        has_json = any(ext in [".json", ".gz"] for ext in file_extensions)
        self.assertTrue(has_json)
        self.assertIn(".txt", file_extensions)


if __name__ == "__main__":
    unittest.main()
