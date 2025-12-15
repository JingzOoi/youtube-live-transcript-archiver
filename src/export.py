import opentimelineio as otio
import os

def generate_professional_edl(highlights, video_path, video_fps, output_path, title="Highlights"):
    """
    Generates a frame-accurate EDL using OpenTimelineIO.
    """
    timeline = otio.schema.Timeline(name=title)
    track = otio.schema.Track(name="Video", kind=otio.schema.TrackKind.Video)
    timeline.tracks.append(track)

    # Convert path to absolute for Resolve
    media_url = f"file://{os.path.abspath(video_path)}"
    
    # Create Media Reference
    media_ref = otio.schema.ExternalReference(
        target_url=media_url,
        available_range=otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, video_fps),
            duration=otio.opentime.RationalTime(100000, video_fps) # arbitrary large duration
        )
    )

    for i, (start_sec, end_sec) in enumerate(highlights):
        # Calculate Frame-Accurate Ranges
        start_frame = int(start_sec * video_fps)
        duration_frames = int((end_sec - start_sec) * video_fps)
        
        # Source Range (Where in the original video?)
        src_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(start_frame, video_fps),
            duration=otio.opentime.RationalTime(duration_frames, video_fps)
        )
        
        # Create Clip
        clip = otio.schema.Clip(
            name=f"Highlight_{i+1:03d}",
            media_reference=media_ref,
            source_range=src_range
        )
        track.append(clip)

    # Serialize to CMX 3600 EDL
    otio.adapters.write_to_file(timeline, output_path, adapter_name="cmx_3600")
    print(f"✓ Professional EDL saved to: {output_path}")