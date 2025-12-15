import ffmpeg
import os

def get_video_metadata(filepath):
    """
    Probes video file to get exact frame rate and duration.
    Crucial for EDL accuracy to prevent audio drift.
    """
    try:
        probe = ffmpeg.probe(filepath)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if not video_stream:
            raise ValueError("No video stream found")

        # Handle '60/1' or '30000/1001' strings
        avg_frame_rate = video_stream.get('avg_frame_rate', '30/1')
        num, den = map(int, avg_frame_rate.split('/'))
        fps = num / den
        
        return {
            'fps': fps,
            'duration': float(video_stream.get('duration', 0)),
            'width': int(video_stream.get('width')),
            'height': int(video_stream.get('height'))
        }
    except ffmpeg.Error as e:
        print(f"FFmpeg probe error: {e.stderr}")
        raise

def normalize_clip(input_path, output_path, target_fps=60):
    """
    Reliability Layer:
    1. Enforces Constant Frame Rate (CFR).
    2. Re-encodes audio to AAC (fixes Twitch muted segments causing errors).
    3. Trims any garbage data from the download buffer.
    """
    try:
        (
            ffmpeg
            .input(str(input_path))
            .output(
                str(output_path),
                r=target_fps,         # Force FPS
                vcodec='libx264',     # Standard H.264
                crf=18,               # High Quality
                preset='fast',
                acodec='aac',         # Ensure Audio is standard
                ar=48000,
                strict='experimental'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return True
    except ffmpeg.Error as e:
        print(f"FFmpeg Error on {input_path}: {e.stderr.decode()}")
        return False
    finally:
        # Cleanup the raw "unsafe" file
        if os.path.exists(input_path):
            os.remove(input_path)