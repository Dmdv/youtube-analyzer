# YouTube Analyzer

Extract transcripts from YouTube videos and analyze them with AI via Poe API.

## Installation

```bash
cd ~/youtube-analyzer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

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
# Basic summary (default mode, uses gpt-5.2-pro)
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

Each mode sends the **entire transcript** in a single request with a different prompt tailored to extract specific information. This is not chunking - the full context goes to the AI with different instructions.

| Mode | Description |
|------|-------------|
| `summary` | Concise 2-3 sentence summary with key takeaway (default) |
| `detailed` | Full breakdown: overview, key points, quotes, context |
| `sentiment` | Analyze tone, emotion, speaker attitude |
| `topics` | Extract keywords, categories, related topics |
| `chapters` | Generate chapter timestamps from content |
| `qa` | Answer a specific question about the video |
| `raw` | Output transcript only (no AI analysis) |
| `seed` | Generate comprehensive architecture seed document |

### Summary Mode (default)

Quick overview ideal for deciding if a video is worth watching.

**Output includes:**
1. A concise 2-3 sentence summary
2. The main takeaway or key message
3. Who would benefit from watching

```bash
python youtube_analyzer.py URL --mode summary
```

**Example output:**
```
1. This interview covers how the speaker achieved top results in a coding challenge
   using an open model, reaching performance close to top proprietary agents.

2. High-performing agents are less about "bigger models" and more about
   managing context and process.

3. AI engineers building tool-using agents who want practical patterns
   for reliability and accuracy.
```

### Detailed Mode

Comprehensive breakdown for deep understanding of video content.

**Output includes:**
1. Overview (2-3 sentences)
2. Key Points (bullet list)
3. Notable Quotes (significant statements)
4. Context (background knowledge needed)
5. Conclusion/Takeaway

```bash
python youtube_analyzer.py URL --mode detailed
```

### Sentiment Mode

Analyze the emotional tone and speaker dynamics.

**Output includes:**
1. Overall Tone (educational, entertaining, persuasive, controversial)
2. Emotional Sentiment (positive/negative/neutral with explanation)
3. Speaker's Attitude (confident, uncertain, passionate, etc.)
4. Audience Engagement Style
5. Notable Emotional Moments

```bash
python youtube_analyzer.py URL --mode sentiment
```

### Topics Mode

Extract structured metadata about video content.

**Output includes:**
1. Primary Topic (main subject)
2. Secondary Topics (supporting themes)
3. Keywords (10-15 important terms)
4. Categories (video classification)
5. Related Topics (viewer interests)

```bash
python youtube_analyzer.py URL --mode topics
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

Generate YouTube chapter timestamps based on topic shifts.

**How it works:**
- Uses timestamps from the transcript
- Identifies major topic transitions
- Creates 5-10 chapters for typical videos

```bash
python youtube_analyzer.py URL --mode chapters
```

**Example output:**
```
[00:00] Introduction and Guest Presentation
[06:00] Challenge Overview and Benchmark Structure
[19:00] Solution Architecture: Context Preparation
[32:00] System Prompt Formation and Tool Filtering
[42:00] Plan-React Agent and Structured Output
[54:00] Solution Evolution and Validation
[76:00] Context Optimization and Dialog Management
[95:00] Multi-Agent System with Orchestrator
[103:00] Conclusion: Model Comparison and Results
```

### Q&A Mode

Ask specific questions about video content.

```bash
python youtube_analyzer.py URL --mode qa --question "What tools does the speaker recommend?"
python youtube_analyzer.py URL -m qa -q "How does the authentication work?"
```

**Note:** The AI will answer based only on transcript content and indicate if the information isn't present.

### Raw Mode

Output transcript without AI analysis - useful for:
- Reviewing content before analysis
- Using with other tools
- Saving transcripts locally

```bash
python youtube_analyzer.py URL --mode raw
python youtube_analyzer.py URL --mode raw --no-timestamps  # Plain text
```

### Seed Mode

Generate comprehensive architecture seed documents for development. Ideal for:
- Technical talks and conference presentations
- Architecture discussions and design reviews
- Tutorial videos with implementation details
- Creating development documentation from video content

**Output includes:**
1. Executive Summary (topic, problem, solution)
2. Architectural Patterns & Decisions
3. Key Insights & Takeaways
4. Terminology & Keywords with definitions
5. Implementation Recommendations
6. Evolution & Iterations (if discussed)
7. Development Roadmap
8. References & Resources

```bash
python youtube_analyzer.py URL --mode seed

# Save to file for further development
python youtube_analyzer.py URL --mode seed > SEED_DOCUMENT.md
```

**Example output:**
```markdown
## 1. EXECUTIVE SUMMARY
- Main topic: AI Agent Architecture for Enterprise Applications
- Problem: Building reliable agents that maintain context
- Solution: Multi-stage pipeline with validators and orchestration

## 2. ARCHITECTURAL PATTERNS & DECISIONS
### Pattern: Plan-React Agent
- Description: Agent that creates execution plan before acting
- Trade-offs: More structured but higher latency
- Implementation: Separate planning and execution phases
...
```

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

# Create architecture seed document from a technical talk
python youtube_analyzer.py URL --mode seed > docs/ARCHITECTURE_SEED.md
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
├── youtube_analyzer.py   # Main script (487 lines)
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── ARCHITECTURE.md      # Detailed implementation documentation
├── RESEARCH.md          # Background research on tools/approaches
├── CHANGESET.md         # Git commit history
├── .env                 # API key (gitignored)
├── .gitignore           # Ignored files
└── .venv/               # Virtual environment
```

## Architecture

For detailed technical documentation including:
- System architecture diagrams
- Complete prompt templates for each mode
- Error handling strategies
- Performance notes and limitations

See [ARCHITECTURE.md](ARCHITECTURE.md).
