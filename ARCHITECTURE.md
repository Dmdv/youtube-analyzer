# YouTube Analyzer - Architecture & Implementation Details

## Overview

YouTube Analyzer is a Python CLI tool that extracts transcripts from YouTube videos and analyzes them using AI models via the Poe API. It supports multiple analysis modes and automatic model fallback for reliability.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YouTube Analyzer Flow                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐    ┌─────────┐
│              │    │                   │    │                  │    │         │
│  YouTube     │───▶│  Transcript       │───▶│  Format          │───▶│  Poe    │
│  URL/ID      │    │  Extraction       │    │  Transcript      │    │  API    │
│              │    │                   │    │                  │    │         │
└──────────────┘    └───────────────────┘    └──────────────────┘    └─────────┘
                            │                                              │
                            ▼                                              ▼
                    ┌───────────────────┐                        ┌─────────────────┐
                    │ youtube-transcript│                        │ OpenAI-compatible│
                    │ -api v1.x         │                        │ endpoint         │
                    │ OR                │                        │                  │
                    │ Whisper fallback  │                        │ gpt-5.2-pro     │
                    └───────────────────┘                        │ claude-sonnet-4.5│
                                                                 └─────────────────┘
```

## Components

### 1. Video ID Extraction (`extract_video_id`)

Parses various YouTube URL formats to extract the 11-character video ID:

```python
# Supported formats:
https://youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://youtube.com/embed/VIDEO_ID
VIDEO_ID  # Just the ID directly
```

**Regex patterns used:**
```python
patterns = [
    r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
    r'^([a-zA-Z0-9_-]{11})$',  # Just the ID
]
```

### 2. Transcript Extraction

#### Primary: YouTube Transcript API (v1.x)

Uses `youtube-transcript-api` library with instance-based API:

```python
from youtube_transcript_api import YouTubeTranscriptApi

ytt_api = YouTubeTranscriptApi()
transcript_list = ytt_api.list(video_id)
```

**Transcript priority order:**
1. Manual English transcript (`en`, `en-US`, `en-GB`)
2. Auto-generated English transcript
3. Any manual transcript (any language)
4. Any auto-generated transcript

**Return format (v1.x):**
```python
# Returns list of FetchedTranscriptSnippet objects:
FetchedTranscriptSnippet(
    text='Hello world',
    start=2.72,      # seconds
    duration=4.159   # seconds
)
```

#### Fallback: Whisper Transcription

If no YouTube captions exist, the script can use OpenAI Whisper:

```bash
# 1. Download audio with yt-dlp
yt-dlp -x --audio-format mp3 -o audio.mp3 "VIDEO_URL"

# 2. Transcribe with Whisper
whisper audio.mp3 --model base --output_format json
```

**Requirements for Whisper fallback:**
- `yt-dlp` (install: `brew install yt-dlp`)
- `openai-whisper` (install: `pip install openai-whisper`)
- `ffmpeg` (install: `brew install ffmpeg`)

### 3. Transcript Formatting (`format_transcript`)

Converts transcript segments to readable text. Supports both dict format (Whisper) and object format (API v1.x):

```python
def get_text(seg) -> str:
    return seg.text if hasattr(seg, 'text') else seg['text']

def get_start(seg) -> float:
    return seg.start if hasattr(seg, 'start') else seg['start']
```

**Output formats:**

With timestamps (default):
```
[00:02] Hello and welcome to the video
[00:05] Today we'll discuss AI agents
[00:08] Let's get started
```

Without timestamps (`--no-timestamps`):
```
Hello and welcome to the video Today we'll discuss AI agents Let's get started
```

### 4. Preflight Check (`preflight_check`)

Tests API connectivity before processing the full transcript:

```python
def preflight_check(api_key: str, model: str) -> bool:
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.poe.com/v1",
        timeout=30.0,
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=16,  # Some models require min 16 tokens
        messages=[{"role": "user", "content": "Hi"}],
    )
    return True  # or False on exception
```

**Fallback logic:**
```
1. Try primary model (gpt-5.2-pro)
   ├─ Success → Use primary model
   └─ Fail → Try fallback model (claude-sonnet-4.5)
              ├─ Success → Use fallback model
              └─ Fail → Exit with error
```

### 5. AI Analysis (`analyze_with_ai`)

Sends transcript to Poe API with mode-specific prompts:

```python
client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.poe.com/v1",
    timeout=60.0,
)

# Streaming response for long content
with client.chat.completions.create(
    model=active_model,
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}],
    stream=True,
) as stream:
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            response_text += chunk.choices[0].delta.content
```

## Analysis Modes

### Summary Mode (default)
**Purpose:** Quick overview of video content

**Prompt:**
```
Analyze this YouTube video transcript and provide:
1. A concise 2-3 sentence summary
2. The main takeaway or key message
3. Who would benefit from watching this video

Transcript:
{transcript}
```

**Example output:**
```
1. This interview covers how Ilya Ris achieved top results in ERC3 using
   an open model, reaching performance close to top proprietary agents.

2. High-performing agents are less about "bigger models" and more about
   managing context and process.

3. AI engineers building tool-using agents who want practical patterns
   for reliability and accuracy.
```

### Detailed Mode
**Purpose:** Comprehensive breakdown with key points and quotes

**Prompt:**
```
Analyze this YouTube video transcript and provide a detailed breakdown:

1. **Overview** (2-3 sentences)
2. **Key Points** (bullet list of main ideas)
3. **Notable Quotes** (if any significant statements)
4. **Context** (what background knowledge helps understand this)
5. **Conclusion/Takeaway**

Transcript:
{transcript}
```

### Sentiment Mode
**Purpose:** Analyze tone, emotion, and speaker attitude

**Prompt:**
```
Analyze the sentiment and tone of this YouTube video transcript:

1. **Overall Tone** (e.g., educational, entertaining, persuasive, controversial)
2. **Emotional Sentiment** (positive/negative/neutral with explanation)
3. **Speaker's Attitude** (confident, uncertain, passionate, etc.)
4. **Audience Engagement Style** (how does the speaker connect with viewers)
5. **Notable Emotional Moments** (any peaks in intensity)

Transcript:
{transcript}
```

### Topics Mode
**Purpose:** Extract keywords, categories, and themes

**Prompt:**
```
Extract the main topics and keywords from this YouTube video transcript:

1. **Primary Topic** (the main subject)
2. **Secondary Topics** (supporting themes)
3. **Keywords** (10-15 important terms, comma-separated)
4. **Categories** (what categories would this video fit in)
5. **Related Topics** (what else might viewers be interested in)

Transcript:
{transcript}
```

**Example output:**
```
1. Primary Topic: AI Agent Architecture for Enterprise Applications

2. Secondary Topics:
   - Context engineering and management
   - Multi-agent orchestration patterns
   - Open-source vs proprietary model comparison

3. Keywords: agents, context engineering, RAG, validators, orchestrator,
   multi-agent, tool calling, structured output, LLM, enterprise

4. Categories: AI/ML Engineering, Software Architecture, Enterprise AI

5. Related Topics: LangChain, prompt engineering, production ML systems
```

### Chapters Mode
**Purpose:** Generate chapter timestamps based on content shifts

**Prompt:**
```
Based on this YouTube video transcript, generate chapter timestamps.

The transcript includes timestamps. Create logical chapter breaks with:
- Timestamp (use the closest timestamp from the transcript)
- Chapter title (concise, descriptive)

Format each chapter as:
[MM:SS] Chapter Title

Aim for 5-10 chapters depending on video length. Focus on major topic shifts.

Transcript:
{transcript}
```

**Example output:**
```
[00:00] Introduction and Guest Presentation
[06:00] ERC3 Challenge Overview and Benchmark Structure
[19:00] Solution Architecture: Context Preparation Stage
[32:00] System Prompt Formation and Tool Filtering
[42:00] Plan-React Agent and Structured Output
[54:00] Solution Evolution and Agent Validator
[76:00] Context Optimization and Dialog History Management
[95:00] Multi-Agent System with Orchestrator
[103:00] Conclusion: Model Comparison and Results
```

### Q&A Mode
**Purpose:** Answer specific questions about video content

**Prompt:**
```
Based on this YouTube video transcript, answer the following question:

Question: {question}

Provide a clear, direct answer based only on information from the transcript.
If the answer isn't in the transcript, say so.

Transcript:
{transcript}
```

**Usage:**
```bash
python youtube_analyzer.py URL --mode qa --question "What tools does the speaker recommend?"
```

### Seed Mode
**Purpose:** Generate comprehensive architecture seed documents for development

**Prompt:**
```
Analyze this video transcript and create a comprehensive SEED DOCUMENT for software development.

Extract and organize ALL of the following:

## 1. EXECUTIVE SUMMARY
- Main topic and purpose of the content
- Key problem being solved
- Primary solution approach

## 2. ARCHITECTURAL PATTERNS & DECISIONS
For each pattern/architecture discussed:
- Pattern name and description
- Why it was chosen (trade-offs considered)
- How it works (implementation approach)
- Benefits and limitations

## 3. KEY INSIGHTS & TAKEAWAYS
- Technical insights (numbered list)
- Strategic insights
- Lessons learned
- Best practices mentioned

## 4. TERMINOLOGY & KEYWORDS
- Technical terms with definitions
- Domain-specific vocabulary
- Acronyms and their meanings

## 5. IMPLEMENTATION RECOMMENDATIONS
- Step-by-step approach if mentioned
- Tools and technologies recommended
- Configuration or setup notes
- Code patterns or examples discussed

## 6. EVOLUTION & ITERATIONS
- How the solution evolved (if discussed)
- Version history or iterations
- What didn't work and why

## 7. DEVELOPMENT ROADMAP
- Suggested next steps
- Future improvements mentioned
- Areas for further research

## 8. REFERENCES & RESOURCES
- Any tools, libraries, or frameworks mentioned
- External resources referenced
- Related topics to explore

Format with clear markdown headers and bullet points.
If certain sections have no relevant content, note "Not discussed in video."

Transcript:
{transcript}
```

**Usage:**
```bash
# Generate seed document
python youtube_analyzer.py URL --mode seed

# Save to file for further development
python youtube_analyzer.py URL --mode seed > docs/ARCHITECTURE_SEED.md
```

**Notes:**
- Uses 8192 max_tokens (vs 4096 for other modes) for comprehensive output
- Ideal for technical talks, architecture discussions, and tutorial videos
- Output is formatted as markdown, ready for use as development documentation

### Raw Mode
**Purpose:** Output transcript only (no AI analysis)

Simply outputs the formatted transcript without sending to AI. Useful for:
- Reviewing transcript before analysis
- Using transcript with other tools
- Saving transcripts locally

## Available Models (Poe API - January 2026)

| Model | Description | Context |
|-------|-------------|---------|
| `gpt-5.2-pro` | **Default** - Most capable GPT | 256K |
| `claude-sonnet-4.5` | **Fallback** - Anthropic Claude | 256K |
| `gpt-5.2` | Fast GPT-5 variant | 256K |
| `gpt-5.1` | Previous GPT-5 version | 256K |
| `gpt-5.1-codex` | Code-optimized GPT-5 | 256K |
| `gpt-5.1-codex-max` | Max context code model | 256K |
| `claude-sonnet-4` | Previous Claude version | 256K |
| `claude-sonnet-4-reasoning` | Reasoning-focused Claude | 256K |
| `gpt-4.1` | GPT-4 series | 256K |
| `gpt-4.1-mini` | Smaller GPT-4 | 256K |

## Error Handling

### API Errors

| Error Type | Behavior |
|------------|----------|
| `AuthenticationError` | Exit immediately (invalid API key) |
| `RateLimitError` | Exit with message (500 req/min limit) |
| `APIConnectionError` | Exit immediately (network issue) |
| `APIStatusError` | Exit with error details |

### Transcript Errors

| Error Type | Behavior |
|------------|----------|
| `TranscriptsDisabled` | Try Whisper fallback |
| `NoTranscriptFound` | Try Whisper fallback |
| `VideoUnavailable` | Exit with error |
| Empty transcript | Exit with error |

### Long Transcript Warning

For transcripts over ~100,000 tokens (estimated as `len(transcript) // 4`):
```
Warning: Transcript is very long (~150,000 tokens).
Analysis may be truncated or fail.
```

## Configuration

### Environment Variables

```bash
# Required
export POE_API_KEY="your-key-here"
```

### .env File Support

Create `.env` in project directory:
```
POE_API_KEY="your-key-here"
```

Load before running:
```bash
source .env && export POE_API_KEY
python youtube_analyzer.py URL
```

## CLI Reference

```bash
python youtube_analyzer.py <url> [options]

Arguments:
  url                   YouTube URL or video ID

Options:
  --mode, -m MODE       Analysis mode (default: summary)
                        Choices: summary, detailed, sentiment, topics,
                                 chapters, qa, raw
  --model MODEL         AI model to use (default: gpt-5.2-pro)
  --question, -q TEXT   Question for Q&A mode (required if mode=qa)
  --no-timestamps       Exclude timestamps from output
  --whisper             Force Whisper even if captions exist
  -h, --help            Show help message
```

## Examples

```bash
# Basic summary
python youtube_analyzer.py "https://youtu.be/VIDEO_ID"

# Detailed breakdown with Claude
python youtube_analyzer.py URL --mode detailed --model claude-sonnet-4.5

# Generate chapters
python youtube_analyzer.py URL --mode chapters

# Ask a question
python youtube_analyzer.py URL --mode qa --question "What are the main points?"

# Just get transcript
python youtube_analyzer.py URL --mode raw

# Force Whisper transcription
python youtube_analyzer.py URL --whisper
```

## File Structure

```
youtube-analyzer/
├── youtube_analyzer.py   # Main script (487 lines)
├── requirements.txt      # Python dependencies
├── README.md            # Quick start guide
├── RESEARCH.md          # Background research on tools
├── ARCHITECTURE.md      # This file
├── CHANGESET.md         # Git commit history
├── .env                 # API key (gitignored)
├── .gitignore           # Ignored files
└── .venv/               # Virtual environment
```

## Dependencies

**Core (required):**
```
youtube-transcript-api>=1.2.0   # YouTube captions extraction
openai>=1.0.0                   # Poe API client (OpenAI-compatible)
```

**Optional (Whisper fallback):**
```
openai-whisper>=20231117        # Speech-to-text
yt-dlp                          # YouTube downloader (brew install)
ffmpeg                          # Audio processing (brew install)
```

## Performance Notes

1. **Transcript Fetch:** ~1-3 seconds for most videos
2. **Preflight Check:** ~2-5 seconds (tests API connectivity)
3. **Analysis Time:** Depends on transcript length and model
   - Short videos (5-10 min): ~10-20 seconds
   - Long videos (1+ hour): ~30-60 seconds
4. **Streaming:** Responses stream in real-time for immediate feedback

## Limitations

1. **No captions = Whisper required:** Some videos have disabled captions
2. **Language:** Works best with English; other languages depend on model capability
3. **Token limits:** Very long videos may hit model context limits
4. **Rate limits:** Poe API allows 500 requests/minute
5. **Connection timeouts:** Long analyses may timeout (60s default)
