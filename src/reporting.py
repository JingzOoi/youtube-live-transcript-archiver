# -*- coding: utf-8 -*-
"""
Enhanced report generation system for YouTube Live Transcript Archiver.
Supports HTML, JSON, and text formats with interactive features.
"""

import json
import gzip
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils import Logger


class ReportGenerator:
    """Enhanced report generator supporting multiple formats."""

    def __init__(self, output_dir: str, config: Dict[str, Any]):
        self.output_dir = output_dir
        self.config = config

    def generate_reports(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Generate all configured report formats."""
        generated_files = []

        formats = self.config.get("REPORT_FORMAT", "html").split(",")

        for format_type in formats:
            format_type = format_type.strip()

            if format_type == "all":
                # Generate all formats
                all_formats = ["html", "json", "txt"]
                for fmt in all_formats:
                    reporter = None
                    if fmt == "html":
                        reporter = HTMLReporter(self.output_dir, self.config)
                    elif fmt == "json":
                        reporter = OptimizedJSONReporter(self.output_dir, self.config)
                    elif fmt == "txt":
                        reporter = TextReporter(self.output_dir, self.config)

                    if reporter:
                        try:
                            file_path = reporter.generate_report(analysis_data)
                            generated_files.append(file_path)
                        except Exception as e:
                            Logger.error(f"Failed to generate {fmt} report: {e}")
                continue  # Skip the else clause for "all"

            elif format_type == "html":
                reporter = HTMLReporter(self.output_dir, self.config)
                file_path = reporter.generate_report(analysis_data)
                generated_files.append(file_path)
            elif format_type == "json":
                reporter = OptimizedJSONReporter(self.output_dir, self.config)
                file_path = reporter.generate_report(analysis_data)
                generated_files.append(file_path)
            elif format_type == "txt":
                reporter = TextReporter(self.output_dir, self.config)
                file_path = reporter.generate_report(analysis_data)
                generated_files.append(file_path)
            else:
                Logger.warning(f"Unsupported report format: {format_type}")
                continue

            try:
                file_path = reporter.generate_report(analysis_data)
                generated_files.append(file_path)
                Logger.success(f"Generated {format_type} report: {file_path}")
            except Exception as e:
                Logger.error(f"Failed to generate {format_type} report", e)

        return generated_files


class BaseReporter:
    """Base class for report generators."""

    def __init__(self, output_dir: str, config: Dict[str, Any]):
        self.output_dir = output_dir
        self.config = config


class HTMLReporter(BaseReporter):
    """Generate interactive HTML reports with navigation and charts."""

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate HTML report with interactive features."""

        # Extract data for HTML generation
        run_info = analysis_data.get("run_info", {})
        highlights = analysis_data.get("highlights", [])
        configuration = analysis_data.get("configuration", {})
        data_summary = analysis_data.get("data_summary", {})
        text_replacements = analysis_data.get("text_replacements_applied", {})

        # Create executive summary
        executive_summary = self._create_executive_summary(
            highlights, data_summary, text_replacements
        )

        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stream Analysis Report - {run_info.get("url", "Unknown")}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Modern responsive CSS with theme toggle */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f4f4f; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; display: grid; grid-template-columns: 250px 1fr; gap: 20px; }}
        .sidebar {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; position: sticky; top: 20px; max-height: calc(100vh - 40px); }}
        .sidebar h1 {{ margin: 0 0 10px 0; color: #333; font-size: 18px; }}
        .sidebar a {{ display: block; padding: 8px 12px; margin: 4px 0; background: #3498db; color: white; text-decoration: none; border-radius: 4px; font-size: 14px; transition: all 0.3s; }}
        .sidebar a:hover {{ background: #1a73e8; transform: translateX(2px); }}
        .main {{ background: white; padding: 20px; border-radius: 8px; }}
        .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; display: block; margin-bottom: 5px; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .insights-section {{ background: #e9ecef; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .insights-list {{ list-style: none; padding: 0; }}
        .insights-list li {{ padding: 8px 0; margin-bottom: 8px; background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px; }}
        .highlight {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #dee2e6; }}
        .highlight-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .highlight-time {{ font-weight: bold; color: #007bff; }}
        .highlight-duration {{ color: #666; }}
        .transcript-content {{ font-family: 'Courier New', monospace; background: #f8f9fa; padding: 15px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #dee2e6; padding-bottom: 10px; }}
        .timeline-chart {{ height: 300px; margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #666; }}
        @media (max-width: 768px) {{ .container {{ grid-template-columns: 1fr; }} .sidebar {{ position: relative; max-height: none; }} }}
    </style>
</head>
<body>
    <div class="container">
        <nav class="sidebar">
            <h1>📊 Analysis Report</h1>
            <a href="#executive-summary">📈 Executive Summary</a>
            <a href="#highlights-timeline">⭐ Highlights</a>
            <a href="#transcript-analysis">📝 Transcript</a>
            <a href="#processing-details">⚙️ Processing</a>
            <a href="#configuration">⚙️ Configuration</a>
        </nav>
        
        <main>
            {executive_summary}
            
            <section id="highlights-timeline">
                <h1>⭐ Highlight Timeline</h1>
                <div class="timeline-chart">
                    <canvas id="timelineChart"></canvas>
                </div>
                
                <div class="highlights-list">
                    {self._create_highlight_cards(highlights)}
                </div>
            </section>
            
            <section id="transcript-analysis">
                <h1>📝 Transcript Analysis</h1>
                {self._create_transcript_section(analysis_data)}
            </section>
            
            <section id="processing-details">
                <h1>⚙️ Processing Details</h1>
                <table>
                    <tr><th>Step</th><th>Timestamp</th><th>Details</th></tr>
                    {self._create_processing_steps_table(analysis_data)}
                </table>
            </section>
            
            <section id="configuration">
                <h1>⚙️ Configuration</h1>
                <table>
                    <tr><th>Setting</th><th>Value</th></tr>
                    {self._create_configuration_table(configuration)}
                </table>
            </section>
        </main>
    </div>
    
    <script>
        // Interactive features
        document.addEventListener('DOMContentLoaded', function() {{
            const highlights = {json.dumps(highlights)};
            const ctx = document.getElementById('timelineChart').getContext('2d');
            
            if (ctx) {{
                // Create timeline chart
                const timelineData = highlights.map((h, index) => ({{
                    x: h.start_seconds,
                    y: 0,
                    width: h.duration
                    highlight: h
                }}));
                
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: highlights.map(h => `Clip ${{h.id}}`),
                        datasets: [{{
                            label: 'Duration (s)',
                            data: highlights.map(h => h.duration),
                            backgroundColor: '#007bff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            x: {{ 
                                title: 'Time (seconds)',
                                type: 'linear'
                            }},
                            y: {{
                                title: 'Duration',
                                beginAtZero: true
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        const highlight = highlights[context.dataIndex];
                                        return `Clip ${{highlight.id}}\\nStart: ${{Math.floor(h.start_seconds / 60)}}:${{(h.start_seconds % 60).toString().padStart(2, '0')}}\\nDuration: ${{h.duration}}s\\nTranscript: ${{highlight.transcript_excerpt ? highlight.transcript_excerpt.substring(0, 100) + '...' : 'No transcript'}}`;
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        }});
        
        // Search functionality
        function createSearchBox() {{
            const searchInput = document.createElement('input');
            searchInput.type = 'search';
            searchInput.placeholder = 'Search highlights...';
            searchInput.style.cssText = 'padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;';
            
            searchInput.addEventListener('input', function(e) {{
                const searchTerm = e.target.value.toLowerCase();
                const filteredHighlights = highlights.filter(h => 
                    h.transcript_excerpt && h.transcript_excerpt.toLowerCase().includes(searchTerm)
                );
                
                // Hide all highlights
                document.querySelectorAll('.highlight').forEach(el => el.style.display = 'none');
                
                // Show matching highlights
                filteredHighlights.forEach(h => {{
                    const element = document.querySelector(`[data-highlight-id="${{h.id}}"]`);
                    if (element) element.style.display = 'block';
                }});
            }});
            
            return searchInput;
        }}
        
        // Add search box to highlights section
        const highlightsSection = document.getElementById('highlights-timeline');
        if (highlightsSection) {{
            const searchContainer = document.createElement('div');
            searchContainer.style.cssText = 'margin-bottom: 20px;';
            searchContainer.appendChild(createSearchBox());
            highlightsSection.parentNode.insertBefore(searchContainer, highlightsSection.firstChild);
        }}
    </script>
</body>
</html>"""

        # Write to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{timestamp}.html"
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path

    def _create_executive_summary(
        self, highlights: List[Dict], data_summary: Dict, replacements: Dict
    ) -> str:
        """Create executive summary HTML."""
        total_highlights = len(highlights)
        total_duration = sum(h.get("duration", 0) for h in highlights)
        avg_duration = total_duration / total_highlights if total_highlights > 0 else 0

        replacement_count = sum(
            stats.get("count", 0) for stats in replacements.values()
        )

        return f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Total Highlights</h3>
                    <span class="metric-value">{total_highlights}</span>
                </div>
                <div class="metric-card">
                    <h3>Total Duration</h3>
                    <span class="metric-value">{total_duration:.1f}s</span>
                </div>
                <div class="metric-card">
                    <h3>Average Duration</h3>
                    <span class="metric-value">{avg_duration:.1f}s</span>
                </div>
                <div class="metric-card">
                    <h3>Chat Messages</h3>
                    <span class="metric-value">{data_summary.get("chat_messages", 0):,}</span>
                </div>
                <div class="metric-card">
                    <h3>Transcript Segments</h3>
                    <span class="metric-value">{data_summary.get("transcript_segments", 0):,}</span>
                </div>
            </div>
            
            <div class="insights-section">
                <h2>🔍 Key Insights</h2>
                <ul class="insights-list">
                    <li><strong>Text Replacements:</strong> {replacement_count} replacements applied</li>
                    <li><strong>Peak Activity:</strong> First highlight typically indicates most engaging content</li>
                    <li><strong>Average Duration:</strong> {avg_duration:.1f}s per highlight</li>
                </ul>
            </div>
        """

    def _create_highlight_cards(self, highlights: List[Dict]) -> str:
        """Create highlight cards with expandable transcripts."""
        cards = []

        for i, highlight in enumerate(highlights, 1):
            start_time = highlight.get("start_seconds", 0)
            duration = highlight.get("duration", 0)
            transcript_excerpt = highlight.get(
                "transcript_excerpt", "No transcript available"
            )

            cards.append(f"""
                <div class="highlight" data-highlight-id="{highlight.get("id", i + 1)}">
                    <div class="highlight-header">
                        <span class="highlight-time">Clip {i + 1}: {self._format_time(start_time)} - {self._format_time(start_time + duration)}</span>
                        <span class="highlight-duration">({duration}s)</span>
                    </div>
                    
                    <div class="transcript-content">
                        <strong>Transcript:</strong><br>
                        {transcript_excerpt[:300]}{"..." if len(transcript_excerpt) > 300 else ""}
                    </div>
                </div>
            """)

        return "".join(cards)

    def _create_transcript_section(self, analysis_data: Dict) -> str:
        """Create transcript analysis section."""
        # Support both transcript_df and transcript_data (from main pipeline)
        transcript_df = analysis_data.get("transcript_df")
        if transcript_df is None:
            transcript_data = analysis_data.get("transcript_data", [])
            if transcript_data:
                transcript_df = pd.DataFrame(transcript_data)

        if transcript_df is None or transcript_df.empty:
            return "<p>No transcript data available for analysis.</p>"

        # Basic transcript statistics
        word_count = 0
        for text in transcript_df.get("text", []):
            word_count += len(text.split())

        return f"""
            <h3>Transcript Statistics</h3>
            <p><strong>Total segments:</strong> {len(transcript_df)}</p>
            <p><strong>Total words:</strong> {word_count:,}</p>
            <p><strong>Average words per segment:</strong> {word_count / len(transcript_df):.1f}</p>
        """

    def _create_processing_steps_table(self, analysis_data: Dict) -> str:
        """Create processing steps table."""
        steps = analysis_data.get("processing_steps", [])

        rows = []
        for step in steps:
            details = step.get("details", {})
            details_str = "<br>".join([f"• {k}: {v}" for k, v in details.items()])

            rows.append(f"""
                <tr>
                    <td>{step.get("step", "Unknown")}</td>
                    <td>{step.get("timestamp", "Unknown")}</td>
                    <td>{details_str}</td>
                </tr>
            """)

        return "".join(rows)

    def _create_configuration_table(self, config: Dict) -> str:
        """Create configuration table."""
        rows = []

        key_settings = [
            ("YouTube URL", config.get("YOUTUBE_URL", "Not set")),
            ("Start Time", config.get("START_TIME_SEC", "None")),
            ("End Time", config.get("END_TIME_SEC", "None")),
            ("Rolling Window", f"{config.get('ROLLING_WINDOW_MIN', 20)} minutes"),
            ("Keywords", ", ".join(config.get("KEYWORDS", []))),
            ("Generate Report", config.get("GENERATE_ANALYSIS_REPORT", True)),
            ("Report Format", config.get("REPORT_FORMAT", "json")),
            (
                "Include Transcript Context",
                config.get("INCLUDE_TRANSCRIPT_CONTEXT", True),
            ),
        ]

        for key, value in key_settings:
            rows.append(f"""
                <tr>
                    <td><strong>{key}</strong></td>
                    <td>{value}</td>
                </tr>
            """)

        return "".join(rows)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"


class OptimizedJSONReporter(BaseReporter):
    """Generate optimized JSON reports with human-readable structure."""

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate optimized JSON report."""

        # Structure data for optimal readability
        structured_data = {
            "metadata": {
                "report_version": "2.0",
                "generated_at": datetime.now().isoformat(),
                "video_info": {
                    "url": analysis_data.get("run_info", {}).get("url", "Unknown"),
                    "duration": analysis_data.get("data_summary", {}).get(
                        "transcript_time_range", "N/A"
                    ),
                },
            },
            "executive_summary": self._create_executive_summary_data(analysis_data),
            "highlights": analysis_data.get("highlights", []),
            "detailed_analysis": {
                "configuration": analysis_data.get("configuration", {}),
                "processing_steps": analysis_data.get("processing_steps", []),
                "text_replacements_applied": analysis_data.get(
                    "text_replacements_applied", {}
                ),
            },
        }

        # Include raw data only if configured
        if self.config.get("REPORT_INCLUDE_RAW_DATA", False):
            structured_data["raw_data"] = analysis_data

        json_content = json.dumps(structured_data, indent=2, ensure_ascii=False)

        # Compress if configured
        if self.config.get("REPORT_COMPRESS_JSON", True):
            filename = (
                f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
            )
            file_path = os.path.join(self.output_dir, filename)

            with gzip.open(file_path, "wt", encoding="utf-8") as f:
                f.write(json_content)
        else:
            filename = (
                f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            file_path = os.path.join(self.output_dir, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_content)

        return file_path

    def _create_executive_summary_data(self, analysis_data: Dict) -> Dict:
        """Create executive summary data."""
        highlights = analysis_data.get("highlights", [])
        data_summary = analysis_data.get("data_summary", {})

        return {
            "total_highlights": len(highlights),
            "total_duration": sum(h.get("duration", 0) for h in highlights),
            "average_duration": sum(h.get("duration", 0) for h in highlights)
            / len(highlights)
            if highlights
            else 0,
            "key_metrics": {
                "chat_messages": data_summary.get("chat_messages", 0),
                "transcript_segments": data_summary.get("transcript_segments", 0),
            },
            "insights": self._generate_insights(highlights, data_summary),
        }

    def _generate_insights(
        self, highlights: List[Dict], data_summary: Dict
    ) -> List[str]:
        """Generate key insights from analysis data."""
        insights = []

        if highlights:
            longest_highlight = max(highlights, key=lambda h: h.get("duration", 0))
            insights.append(
                f"Longest highlight: {longest_highlight.get('duration', 0)}s"
            )

        # Add more insights as needed
        insights.append("Analysis completed with optimized reporting system")

        return insights


class TextReporter(BaseReporter):
    """Generate plain text reports."""

    def generate_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate plain text report."""

        run_info = analysis_data.get("run_info", {})
        highlights = analysis_data.get("highlights", [])
        data_summary = analysis_data.get("data_summary", {})

        text_content = f"""
STREAM ANALYSIS REPORT
====================

Video: {run_info.get("url", "Unknown")}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

EXECUTIVE SUMMARY
- Total Highlights: {len(highlights)}
- Total Duration: {sum(h.get("duration", 0) for h in highlights):.1f}s
- Average Duration: {sum(h.get("duration", 0) for h in highlights) / len(highlights):.1f}s if highlights else 0
- Chat Messages: {data_summary.get("chat_messages", 0):,}
- Transcript Segments: {data_summary.get("transcript_segments", 0):,}

HIGHLIGHTS
{self._create_text_highlights(highlights)}

CONFIGURATION
- Rolling Window: {self.config.get("ROLLING_WINDOW_MIN", 20)} minutes
- Keywords: {", ".join(self.config.get("KEYWORDS", []))}
"""

        # Write to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{timestamp}.txt"
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        return file_path

    def _create_text_highlights(self, highlights: List[Dict]) -> str:
        """Create highlights in text format."""
        lines = []

        for i, highlight in enumerate(highlights, 1):
            start_time = highlight.get("start_seconds", 0)
            duration = highlight.get("duration", 0)
            transcript_excerpt = highlight.get("transcript_excerpt", "No transcript")

            lines.append(
                f"Clip {i + 1}: {self._format_time(start_time)} - {self._format_time(start_time + duration)} ({duration}s)"
            )
            lines.append(
                f"  Transcript: {transcript_excerpt[:200]}{'...' if len(transcript_excerpt) > 200 else ''}"
            )
            lines.append("")

        return "\n".join(lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"
