#!/usr/bin/env python3
"""
YouTube Video Analyzer
Extract transcripts from YouTube videos and analyze them with AI via Poe API.

Usage:
    python youtube_analyzer.py <youtube_url> [--mode MODE] [--model MODEL] [--question QUESTION]

Modes:
    summary     - Generate a concise summary (default)
    detailed    - Detailed breakdown with key points
    sentiment   - Analyze tone and sentiment
    topics      - Extract main topics and keywords
    chapters    - Generate chapter timestamps
    qa          - Ask a specific question (requires --question)
    raw         - Just output the transcript

Models (via Poe API):
    gpt-5.2-pro          - Default, most capable GPT model (256K context)
    claude-sonnet-4.5    - Fallback, Anthropic's Claude (256K context)
    gpt-5.2              - Fast GPT-5 variant
    gpt-5.1-codex        - Code-optimized GPT-5
    claude-sonnet-4      - Previous Claude version
"""

import argparse
import json
import os
import re
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# Available models on Poe API (based on Poe pricing page, Jan 2026)
POE_MODELS = [
    # GPT-5 series (OpenAI)
    "gpt-5.2-pro",
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5.1-codex",
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
    "gpt-5-pro",
    "gpt-5",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-5-codex",
    # Claude series (Anthropic)
    "claude-sonnet-4.5",
    "claude-sonnet-4",
    "claude-sonnet-4-reasoning",
    # GPT-4 series
    "gpt-4.1",
    "gpt-4.1-mini",
]
DEFAULT_MODEL = "gpt-5.2-pro"
FALLBACK_MODEL = "claude-sonnet-4.5"


# Analysis prompts for different modes
ANALYSIS_PROMPTS = {
    "summary": """Analyze this YouTube video transcript and provide:
1. A concise 2-3 sentence summary
2. The main takeaway or key message
3. Who would benefit from watching this video

Transcript:
{transcript}""",

    "detailed": """Analyze this YouTube video transcript and provide a detailed breakdown:

1. **Overview** (2-3 sentences)
2. **Key Points** (bullet list of main ideas)
3. **Notable Quotes** (if any significant statements)
4. **Context** (what background knowledge helps understand this)
5. **Conclusion/Takeaway**

Transcript:
{transcript}""",

    "sentiment": """Analyze the sentiment and tone of this YouTube video transcript:

1. **Overall Tone** (e.g., educational, entertaining, persuasive, controversial)
2. **Emotional Sentiment** (positive/negative/neutral with explanation)
3. **Speaker's Attitude** (confident, uncertain, passionate, etc.)
4. **Audience Engagement Style** (how does the speaker connect with viewers)
5. **Notable Emotional Moments** (any peaks in intensity)

Transcript:
{transcript}""",

    "topics": """Extract the main topics and keywords from this YouTube video transcript:

1. **Primary Topic** (the main subject)
2. **Secondary Topics** (supporting themes)
3. **Keywords** (10-15 important terms, comma-separated)
4. **Categories** (what categories would this video fit in)
5. **Related Topics** (what else might viewers be interested in)

Transcript:
{transcript}""",

    "chapters": """Based on this YouTube video transcript, generate chapter timestamps.

The transcript includes timestamps. Create logical chapter breaks with:
- Timestamp (use the closest timestamp from the transcript)
- Chapter title (concise, descriptive)

Format each chapter as:
[MM:SS] Chapter Title

Aim for 5-10 chapters depending on video length. Focus on major topic shifts.

Transcript:
{transcript}""",

    "qa": """Based on this YouTube video transcript, answer the following question:

Question: {question}

Provide a clear, direct answer based only on information from the transcript.
If the answer isn't in the transcript, say so.

Transcript:
{transcript}""",
}


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',  # Just the ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript_from_api(video_id: str) -> Optional[list]:
    """Get transcript using youtube-transcript-api v1.x (instance-based API)."""
    if not HAS_TRANSCRIPT_API:
        return None

    try:
        # Create API instance (v1.x uses instance methods)
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Priority: manual English > auto English > any manual > any auto
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
            except:
                try:
                    # Try any manually created transcript
                    for t in transcript_list:
                        if not t.is_generated:
                            transcript = t
                            break
                    else:
                        raise Exception("No manual transcript")
                except:
                    # Fall back to any auto-generated transcript
                    for t in transcript_list:
                        if t.is_generated:
                            transcript = t
                            break
                    else:
                        raise Exception("No transcript found")

        return transcript.fetch()

    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except VideoUnavailable:
        print(f"Error: Video {video_id} is unavailable", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not fetch transcript via API: {e}", file=sys.stderr)
        return None


def get_transcript_with_whisper(video_id: str) -> Optional[list]:
    """Download audio and transcribe with Whisper (fallback)."""
    # Check if yt-dlp is available
    if subprocess.run(['which', 'yt-dlp'], capture_output=True).returncode != 0:
        print("Error: yt-dlp not found. Install with: brew install yt-dlp", file=sys.stderr)
        return None

    # Check if whisper is available
    if subprocess.run(['which', 'whisper'], capture_output=True).returncode != 0:
        print("Error: whisper not found. Install with: pip install openai-whisper", file=sys.stderr)
        return None

    print("No captions found. Downloading audio and transcribing with Whisper...", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.mp3"

        # Download audio
        result = subprocess.run([
            'yt-dlp', '-x', '--audio-format', 'mp3',
            '-o', str(audio_path),
            f'https://youtube.com/watch?v={video_id}'
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error downloading audio: {result.stderr}", file=sys.stderr)
            return None

        # Find the actual file (yt-dlp might add extension)
        audio_files = list(Path(tmpdir).glob("audio.*"))
        if not audio_files:
            print("Error: Audio file not found after download", file=sys.stderr)
            return None

        actual_audio = audio_files[0]

        # Transcribe with Whisper
        result = subprocess.run([
            'whisper', str(actual_audio),
            '--model', 'base',
            '--output_format', 'json',
            '--output_dir', tmpdir
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error transcribing: {result.stderr}", file=sys.stderr)
            return None

        # Read the JSON output
        json_path = Path(tmpdir) / f"{actual_audio.stem}.json"
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)

            # Convert to same format as youtube-transcript-api
            segments = []
            for segment in data.get('segments', []):
                segments.append({
                    'text': segment['text'].strip(),
                    'start': segment['start'],
                    'duration': segment['end'] - segment['start']
                })
            return segments

    return None


def format_transcript(segments: list, include_timestamps: bool = True) -> str:
    """Format transcript segments into readable text.

    Supports both dict format (Whisper) and FetchedTranscriptSnippet objects (v1.x API).
    """
    def get_text(seg) -> str:
        return seg.text if hasattr(seg, 'text') else seg['text']

    def get_start(seg) -> float:
        return seg.start if hasattr(seg, 'start') else seg['start']

    if include_timestamps:
        lines = []
        for seg in segments:
            start = get_start(seg)
            minutes = int(start // 60)
            seconds = int(start % 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {get_text(seg)}")
        return '\n'.join(lines)
    else:
        return ' '.join(get_text(seg) for seg in segments)


def preflight_check(api_key: str, model: str) -> bool:
    """Test if the Poe API is responsive with a minimal request."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.poe.com/v1",
        timeout=30.0,
    )

    try:
        # Minimal request to test connectivity and model availability
        response = client.chat.completions.create(
            model=model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return True
    except openai.AuthenticationError:
        print(f"Error: Invalid POE_API_KEY", file=sys.stderr)
        return False
    except openai.RateLimitError:
        print(f"Warning: Rate limit hit for {model}", file=sys.stderr)
        return False
    except openai.APIConnectionError:
        print(f"Error: Could not connect to Poe API", file=sys.stderr)
        return False
    except openai.APIStatusError as e:
        print(f"Warning: Model {model} unavailable: {getattr(e, 'message', str(e))}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Warning: Preflight check failed for {model}: {e}", file=sys.stderr)
        return False


def analyze_with_ai(transcript: str, mode: str, model: str = DEFAULT_MODEL, question: str = "") -> str:
    """Send transcript to Poe API for analysis with automatic fallback."""
    if not HAS_OPENAI:
        print("Error: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get('POE_API_KEY')
    if not api_key:
        print("Error: POE_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key at: https://poe.com/api_key", file=sys.stderr)
        sys.exit(1)

    # Preflight check with fallback logic
    active_model = model
    print(f"Testing API connectivity with {active_model}...", file=sys.stderr)

    if not preflight_check(api_key, active_model):
        if active_model != FALLBACK_MODEL:
            print(f"Trying fallback model: {FALLBACK_MODEL}...", file=sys.stderr)
            active_model = FALLBACK_MODEL
            if not preflight_check(api_key, active_model):
                print("Error: Both primary and fallback models unavailable", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Error: {active_model} not responsive", file=sys.stderr)
            sys.exit(1)

    print(f"API ready. Using model: {active_model}", file=sys.stderr)

    # Warn about very long transcripts (rough estimate: 4 chars per token)
    estimated_tokens = len(transcript) // 4
    if estimated_tokens > 100000:
        print(f"Warning: Transcript is very long (~{estimated_tokens:,} tokens). "
              "Analysis may be truncated or fail.", file=sys.stderr)

    prompt_template = ANALYSIS_PROMPTS.get(mode, ANALYSIS_PROMPTS['summary'])

    if mode == 'qa':
        prompt = prompt_template.format(transcript=transcript, question=question)
    else:
        prompt = prompt_template.format(transcript=transcript)

    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.poe.com/v1",
        timeout=60.0,
    )

    # Streaming analysis with verified model
    response_text = ""
    try:
        with client.chat.completions.create(
            model=active_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ) as stream:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
    except openai.AuthenticationError:
        print("Error: Invalid POE_API_KEY. Check your key at https://poe.com/api_key", file=sys.stderr)
        sys.exit(1)
    except openai.RateLimitError:
        print("Error: Rate limit exceeded. Try again later.", file=sys.stderr)
        sys.exit(1)
    except openai.APIConnectionError:
        print("Error: Could not connect to Poe API. Check your internet connection.", file=sys.stderr)
        sys.exit(1)
    except openai.APIStatusError as e:
        print(f"Error: API request failed: {getattr(e, 'message', str(e))}", file=sys.stderr)
        sys.exit(1)

    return response_text


def main():
    parser = argparse.ArgumentParser(
        description='Analyze YouTube videos with AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://youtube.com/watch?v=VIDEO_ID
  %(prog)s VIDEO_ID --mode detailed
  %(prog)s URL --mode qa --question "What are the main points?"
  %(prog)s URL --mode raw  # Just get the transcript
        """
    )
    parser.add_argument('url', help='YouTube URL or video ID')
    parser.add_argument('--mode', '-m',
                        choices=['summary', 'detailed', 'sentiment', 'topics', 'chapters', 'qa', 'raw'],
                        default='summary',
                        help='Analysis mode (default: summary)')
    parser.add_argument('--question', '-q', help='Question for Q&A mode')
    parser.add_argument('--no-timestamps', action='store_true',
                        help='Exclude timestamps from output')
    parser.add_argument('--whisper', action='store_true',
                        help='Force use of Whisper even if captions exist')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        choices=POE_MODELS,
                        help=f'AI model to use (default: {DEFAULT_MODEL})')

    args = parser.parse_args()

    # Validate Q&A mode has a question
    if args.mode == 'qa' and not args.question:
        print("Error: --question is required for Q&A mode", file=sys.stderr)
        sys.exit(1)

    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"Error: Could not extract video ID from: {args.url}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing video: {video_id}", file=sys.stderr)

    # Get transcript
    segments = None

    if not args.whisper:
        segments = get_transcript_from_api(video_id)

    if segments is None:
        segments = get_transcript_with_whisper(video_id)

    if segments is None:
        print("Error: Could not retrieve transcript", file=sys.stderr)
        sys.exit(1)

    if not segments:
        print("Error: Transcript is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Retrieved {len(segments)} transcript segments", file=sys.stderr)

    # Format transcript
    include_timestamps = args.mode == 'chapters' or not args.no_timestamps
    transcript = format_transcript(segments, include_timestamps)

    # Raw mode just outputs transcript
    if args.mode == 'raw':
        print(transcript)
        return

    # Analyze with AI
    print(f"Analyzing with {args.model} ({args.mode} mode)...", file=sys.stderr)
    result = analyze_with_ai(transcript, args.mode, args.model, args.question or "")

    print("\n" + "="*60)
    print(f"Analysis ({args.mode.upper()})")
    print("="*60 + "\n")
    print(result)


if __name__ == '__main__':
    main()
