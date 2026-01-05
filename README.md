# YouTube Analyzer

Extract transcripts from YouTube videos and analyze them with AI via Poe API.

## Installation

```bash
cd ~/.claude/youtube-analyzer

# Install dependencies
pip install -r requirements.txt

# Set your Poe API key
export POE_API_KEY="your-key-here"
```

### Optional: Whisper Fallback (for videos without captions)

```bash
# Install yt-dlp for downloading
brew install yt-dlp

# Install Whisper for transcription
pip install openai-whisper

# Install ffmpeg (required by Whisper)
brew install ffmpeg
```

## Usage

```bash
# Basic summary (default mode, uses Claude-Sonnet-4)
python youtube_analyzer.py "https://youtube.com/watch?v=VIDEO_ID"

# Different analysis modes
python youtube_analyzer.py URL --mode detailed    # Detailed breakdown
python youtube_analyzer.py URL --mode sentiment   # Tone analysis
python youtube_analyzer.py URL --mode topics      # Extract keywords
python youtube_analyzer.py URL --mode chapters    # Generate timestamps

# Ask a specific question
python youtube_analyzer.py URL --mode qa --question "What are the main points?"

# Just get the transcript (no AI)
python youtube_analyzer.py URL --mode raw

# Force Whisper (even if captions exist)
python youtube_analyzer.py URL --whisper
```

### Model Selection

Choose from multiple AI models via Poe API:

```bash
# Use default (gpt-5.2-pro - most capable)
python youtube_analyzer.py URL

# Use Claude Sonnet 4.5 (fallback model)
python youtube_analyzer.py URL --model claude-sonnet-4.5

# Use GPT-5.2 (faster, cheaper)
python youtube_analyzer.py URL --model gpt-5.2

# Use code-optimized model
python youtube_analyzer.py URL --model gpt-5.1-codex
```

**Available models:**
| Model | Description |
|-------|-------------|
| `gpt-5.2-pro` | **Default** - Most capable GPT (256K context) |
| `claude-sonnet-4.5` | **Fallback** - Anthropic Claude (256K context) |
| `gpt-5.2` | Fast GPT-5 variant |
| `gpt-5.1` | Previous GPT-5 version |
| `gpt-5.1-codex` | Code-optimized GPT-5 |
| `gpt-5.1-codex-max` | Max context code model |
| `claude-sonnet-4` | Previous Claude version |
| `claude-sonnet-4-reasoning` | Reasoning-focused Claude |
| `gpt-4.1` | GPT-4 series |

### Preflight Check & Fallback

The script automatically:
1. **Tests API connectivity** before processing (preflight check)
2. **Falls back to claude-sonnet-4.5** if the primary model is unavailable
3. **Reports clear errors** if both models fail

## Analysis Modes

| Mode | Description |
|------|-------------|
| `summary` | Concise 2-3 sentence summary with key takeaway (default) |
| `detailed` | Full breakdown: overview, key points, quotes, context |
| `sentiment` | Analyze tone, emotion, speaker attitude |
| `topics` | Extract keywords, categories, related topics |
| `chapters` | Generate chapter timestamps from content |
| `qa` | Answer a specific question about the video |
| `raw` | Output transcript only (no AI analysis) |

## Examples

```bash
# Summarize a tech talk
python youtube_analyzer.py "https://youtu.be/dQw4w9WgXcQ" --mode summary

# Get key topics from a podcast
python youtube_analyzer.py "dQw4w9WgXcQ" --mode topics

# Ask about specific content
python youtube_analyzer.py URL -m qa -q "What tools does the speaker recommend?"

# Generate chapters for a long video
python youtube_analyzer.py URL --mode chapters

# Use Claude for detailed analysis
python youtube_analyzer.py URL --mode detailed --model claude-sonnet-4.5
```

## How It Works

1. **Transcript Extraction**: Uses `youtube-transcript-api` to fetch YouTube's built-in captions
2. **Whisper Fallback**: If no captions exist, downloads audio with `yt-dlp` and transcribes with OpenAI Whisper
3. **AI Analysis**: Sends transcript to your chosen AI model via Poe API

## Poe API

This tool uses [Poe's API](https://poe.com/api_pricing) which provides access to multiple AI models through a single OpenAI-compatible endpoint. Get your API key at [poe.com](https://poe.com).

## Files

```
youtube-analyzer/
├── youtube_analyzer.py   # Main script
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── RESEARCH.md          # Background research on tools/approaches
```
