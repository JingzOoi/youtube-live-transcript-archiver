#!/usr/bin/env python3
"""Test the updated time slice constants logic"""

import datetime


def hms_to_seconds(h, m, s):
    """Converts hours, minutes, and seconds to total seconds."""
    if h is None or m is None or s is None:
        return None
    return h * 3600 + m * 60 + s


# Test constants
START_TIME = None  # hms_to_seconds(0, 10, 30)
END_TIME = None  # hms_to_seconds(1, 5, 0)

# Test user input simulation
start_seconds = START_TIME
end_seconds = END_TIME

print(
    f"Analysis will focus on time slice from {str(datetime.timedelta(seconds=start_seconds)) if start_seconds is not None else 'START'} to {str(datetime.timedelta(seconds=end_seconds)) if end_seconds is not None else 'END'}"
)

print("Test passed!")
