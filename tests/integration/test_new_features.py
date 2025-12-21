#!/usr/bin/env python3
"""
Test script to verify transcript retrieval and analysis reporting functionality.
"""

import pandas as pd
import sys
import os

# Add project root to path for imports
sys.path.insert(0, "..")

from src.parsers import get_transcript_segment
from src.utils import AnalysisReporter
import tempfile
import json


def test_transcript_retrieval():
    """Test the get_transcript_segment function."""
    print("Testing transcript retrieval function...")

    # Create test transcript data
    test_transcript = pd.DataFrame(
        {
            "start_time": [
                "00:00:10.000",
                "00:01:30.000",
                "00:02:45.000",
                "00:04:00.000",
            ],
            "end_time": [
                "00:00:15.000",
                "00:01:35.000",
                "00:02:50.000",
                "00:04:05.000",
            ],
            "offset_start_seconds": [10.0, 90.0, 165.0, 240.0],
            "offset_end_seconds": [15.0, 95.0, 170.0, 245.0],
            "text": [
                "First segment",
                "Second segment",
                "Third segment",
                "Fourth segment",
            ],
        }
    )

    # Test full transcript
    full_transcript = get_transcript_segment(test_transcript)
    print(f"✓ Full transcript: {len(full_transcript)} segments")

    # Test time-sliced transcript (60-180 seconds)
    sliced_transcript = get_transcript_segment(test_transcript, 60.0, 180.0)
    print(f"✓ Sliced transcript (60-180s): {len(sliced_transcript)} segments")
    print(f"  Should contain segments 2 and 3: {sliced_transcript['text'].tolist()}")

    # Test start-only slice
    start_only = get_transcript_segment(test_transcript, start_time=100.0)
    print(f"✓ Start-only slice (100s+): {len(start_only)} segments")

    # Test end-only slice
    end_only = get_transcript_segment(test_transcript, end_time=100.0)
    print(f"✓ End-only slice (-100s): {len(end_only)} segments")

    return True


def test_analysis_reporter():
    """Test the AnalysisReporter class."""
    print("\nTesting analysis reporter functionality...")

    # Create temporary directory for test output
    with tempfile.TemporaryDirectory() as temp_dir:
        reporter = AnalysisReporter(temp_dir)

        # Initialize run
        reporter.start_run("https://test.url", dry_run=True)
        print("✓ Run initialized")

        # Test configuration logging
        test_config = {
            "KEYWORDS": ["test", "keyword"],
            "START_TIME_SEC": 30,
            "END_TIME_SEC": 120,
        }
        reporter.log_configuration(test_config)
        print("✓ Configuration logged")

        # Test data summary logging
        test_chat = pd.DataFrame(
            {"offset_seconds": [10, 20, 30], "message": ["msg1", "msg2", "msg3"]}
        )
        test_transcript = pd.DataFrame(
            {
                "offset_start_seconds": [5, 15, 25],
                "offset_end_seconds": [10, 20, 30],
                "text": ["t1", "t2", "t3"],
            }
        )

        reporter.log_data_summary(test_chat, test_transcript)
        print("✓ Data summary logged")

        # Test processing step logging
        reporter.log_processing_step("test_step", {"detail": "test_value"})
        print("✓ Processing step logged")

        # Test highlights logging
        test_ranges = [(30.0, 60.0), (120.0, 150.0)]
        test_spikes = [35.0, 125.0]
        reporter.log_highlights(test_ranges, test_spikes)
        print("✓ Highlights logged")

        # Test transcript context
        reporter.log_transcript_context(1, 30.0, 60.0, test_transcript)
        print("✓ Transcript context logged")

        # Test command logging
        reporter.log_command("test command", "test purpose", True)
        print("✓ Command logged")

        # Test error logging
        reporter.log_error("Test error", None, {"context": "test"})
        print("✓ Error logged")

        # Save and verify report
        report_path = reporter.save_report("test_report.json")
        print(f"✓ Report saved to: {report_path}")

        # Verify report structure
        with open(report_path, "r") as f:
            report_data = json.load(f)

        assert "run_info" in report_data
        assert "configuration" in report_data
        assert "data_summary" in report_data
        assert "processing_steps" in report_data
        assert "highlights" in report_data
        assert "transcript_contexts" in report_data
        assert "commands_run" in report_data
        assert "errors" in report_data

        print("✓ Report structure validated")

    return True


if __name__ == "__main__":
    print("Running implementation tests...\n")

    try:
        # Test transcript retrieval
        transcript_success = test_transcript_retrieval()

        # Test analysis reporter
        reporter_success = test_analysis_reporter()

        if transcript_success and reporter_success:
            print("\n🎉 All tests passed! Implementation is working correctly.")
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
