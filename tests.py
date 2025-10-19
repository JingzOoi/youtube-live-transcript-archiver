# -*- coding: utf-8 -*-
"""
Unit tests for the YouTube Livestream Monitor application.
Run with `python -m unittest test_suite.py`
"""

import unittest
from unittest.mock import patch, mock_open
import os
import tempfile
import json
import parsers
import storage

# --- Test Data Fixtures ---

VTT_FIXTURE = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello everyone and welcome.
<c>This is a test.</c>

00:00:04.100 --> 00:00:06.200
This is the second line.
"""

CHAT_FIXTURE = """
[
    {
        "comment_time_in_seconds": 2,
        "author": {"name": "User1", "id": "UC-123"},
        "text": "First message!"
    },
    {
        "comment_time_in_seconds": 5,
        "author": {"name": "User2", "id": "UC-456"},
        "text": "Hello world"
    },
    {
        "comment_time_in_seconds": 8,
        "author": {"name": "User1", "id": "UC-123"},
        "text": "  Another message  "
    }
]
"""

class TestParsers(unittest.TestCase):
    
    def test_parse_transcript_vtt(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.vtt') as tmp:
            tmp.write(VTT_FIXTURE)
            tmp_path = tmp.name
        
        result = parsers.parse_transcript_vtt(tmp_path)
        os.remove(tmp_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['start_time'], '00:00:01.000')
        self.assertEqual(result[0]['end_time'], '00:00:03.500')
        self.assertEqual(result[0]['text'], 'Hello everyone and welcome. This is a test.')
        self.assertEqual(result[1]['text'], 'This is the second line.')

    def test_parse_live_chat_json(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.json') as tmp:
            tmp.write(CHAT_FIXTURE)
            tmp_path = tmp.name
            
        result = parsers.parse_live_chat_json(tmp_path)
        os.remove(tmp_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['author_name'], 'User1')
        self.assertEqual(result[0]['message'], 'First message!')
        self.assertEqual(result[0]['timestamp_seconds'], 2)
        self.assertEqual(result[0]['timestamp_text'], '0:00:02')
        self.assertEqual(result[2]['message'], 'Another message') # Check stripping whitespace

class TestStorage(unittest.TestCase):

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.makedirs')
    def test_save_data_as_json(self, mock_makedirs, mock_exists, mock_file):
        storage.ensure_directories_exist()
        
        test_data = [{'message': 'test'}]
        storage.save_data_as_json('vid123', 'My Test Video', 'chat', test_data)

        # Check that the correct file path was opened
        mock_file.assert_called_once_with(os.path.join('data', 'chats', 'vid123_My_Test_Video.json'), 'w', encoding='utf-8')
        
        # Check that json.dump was called
        handle = mock_file()
        args, kwargs = handle.write.call_args
        written_data = json.loads(args[0])
        
        self.assertEqual(written_data['videoId'], 'vid123')
        self.assertEqual(written_data['videoTitle'], 'My Test Video')
        self.assertEqual(written_data['dataType'], 'chat')
        self.assertEqual(written_data['data'][0]['message'], 'test')

if __name__ == '__main__':
    unittest.main()
