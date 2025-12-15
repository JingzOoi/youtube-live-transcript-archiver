import os
import yt_dlp
from pathlib import Path

class ContentIngester:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_metadata(self, url: str):
        """Fetches metadata without downloading video."""
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download_chat_and_transcript(self, url: str, video_id: str):
        """Downloads ancillary data using Python API."""
        # Define output template
        out_tmpl = str(self.output_dir / f"{video_id}")
        expected_output = {
            'transcript': self.output_dir / f"{video_id}.en.vtt",
            'chat': self.output_dir / f"{video_id}.live_chat.json"
        }
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'live_chat'],
            'outtmpl': out_tmpl,
            'quiet': True
        }

        if not os.path.exists(expected_output.get("transcript")) or not os.path.exists(expected_output.get("chat")):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
        # Return expected paths
        return expected_output

    def download_video(self, url: str, video_id: str):
        """Downloads video using best MP4 format."""
        out_tmpl = str(self.output_dir / f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': out_tmpl,
            'quiet': False
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
        
    def download_specific_clips(self, url: str, video_id: str, clips: list):
        """
        Downloads specific segments efficiently.
        clips: List of tuples [(start_sec, end_sec), ...]
        """
        downloaded_files = []
        
        # Configure yt-dlp to download segments
        # We use a specific format for the downloader to separate them
        for i, (start, end) in enumerate(clips):
            output_filename = f"{video_id}_raw_clip_{i:03d}"
            out_tmpl = str(self.output_dir / f"{output_filename}.%(ext)s")
            
            print(f"  > Downloading Segment {i+1}: {start:.0f}s - {end:.0f}s")
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': out_tmpl,
                'quiet': True,
                # THIS IS THE MAGIC: Only download the specific range
                'download_ranges': lambda _, __: [{'start_time': start, 'end_time': end}],
                # Force keyframe download so we don't get black screens
                'force_keyframes_at_cuts': True, 
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Find the file (yt-dlp might append ext)
                # We return the path for the next step (Transcoding)
                found = list(self.output_dir.glob(f"{output_filename}.*"))
                if found:
                    downloaded_files.append(found[0])
            except Exception as e:
                print(f"    [!] Failed to download clip {i}: {e}")

        return downloaded_files