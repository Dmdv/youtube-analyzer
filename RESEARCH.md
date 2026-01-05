# YouTube Video Analysis: Extract Transcript + AI Analysis

Based on research conducted on 2026-01-05.

---

## Browser Extensions (Easiest)

| Extension | Key Features | AI Integration |
|-----------|--------------|----------------|
| [Glasp](https://glasp.co/youtube-transcript) | Free, no subscription, works on Chrome/Safari/Edge | ChatGPT, Claude, Mistral - custom prompts |
| [YouTube Transcript AI Summary](https://chromewebstore.google.com/detail/youtube-transcript-ai-sum/eciiehmejcjnbooihpiljfnklkopkfcj) | OpenAI API integration, custom prompts | Automatic summaries, targeted extraction |
| [Merlin AI](https://tubeonai.com/youtube-video-transcription-chrome-extensions/) | Timestamps, highlights, notes | Built-in AI analysis |
| [Fireflies.ai](https://tubeonai.com/youtube-video-transcription-chrome-extensions/) | 60+ languages, exports to DOCX/PDF/JSON | Speaker identification, searchable |

**Recommendation**: Glasp is excellent for Claude integration - you can paste transcripts directly to Claude with custom prompts.

---

## Web-Based Tools (No Install)

| Tool | Features |
|------|----------|
| [NoteGPT](https://notegpt.io/youtube-transcript-generator) | Fast extraction + AI summarization |
| [Kome.ai](https://kome.ai/tools/youtube-transcript-generator) | 120+ languages, AI summaries |
| [youtube-transcript.io](https://www.youtube-transcript.io/) | 25 free transcripts, AI summaries |
| [Tactiq](https://tactiq.io/tools/youtube-transcript) | Real-time transcription, meetings support |

---

## Open Source / Self-Hosted (Privacy + Control)

Best for developers who want full control:

1. **[ai-powered-video-analyzer](https://github.com/arashsajjadi/ai-powered-video-analyzer)** - Fully offline!
   - Whisper for transcription
   - YOLO for object detection
   - Ollama for local LLM analysis
   - GUI included

2. **[yt-transcript-gpt](https://github.com/topics/youtube-transcripts)** - Streamlit app
   - Extract transcripts
   - AI-powered analysis
   - Interactive chat about video content

3. **DIY Pipeline** (most flexible):
   ```
   yt-dlp → Whisper → Claude API
   ```

---

## Build Your Own (Programmatic Approach)

### Key Insight

The most flexible approach combines 3 components:
1. **Transcript extraction**: YouTube's built-in captions OR Whisper for audio
2. **Text processing**: Clean and chunk the transcript
3. **AI analysis**: Send to Claude/GPT for summarization, sentiment, Q&A

### Simple Python Pipeline

```python
# 1. Get transcript (using youtube-transcript-api)
from youtube_transcript_api import YouTubeTranscriptApi

transcript = YouTubeTranscriptApi.get_transcript("VIDEO_ID")
text = " ".join([t['text'] for t in transcript])

# 2. Send to Claude for analysis
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": f"Analyze this video transcript:\n\n{text}"}]
)
```

### For videos without captions (use Whisper):

```bash
yt-dlp -x --audio-format mp3 "VIDEO_URL"
whisper audio.mp3 --model base --output_format txt
```

---

## What Analysis Can AI Do?

| Analysis Type | Use Case |
|--------------|----------|
| **Summarization** | TL;DW (too long; didn't watch) |
| **Sentiment Analysis** | Audience reaction, tone |
| **Key Topics/Keywords** | SEO, content categorization |
| **Q&A** | Ask questions about the content |
| **Entity Extraction** | People, places, products mentioned |
| **Chapter Generation** | Auto-create timestamps |

---

## Recommendations

- **For quick analysis**: [Glasp](https://glasp.co/youtube-transcript) -> Copy transcript -> Paste to Claude
- **For privacy/offline**: [ai-powered-video-analyzer](https://github.com/arashsajjadi/ai-powered-video-analyzer) (runs entirely local with Whisper + Ollama)
- **For automation**: Build a Python script using `youtube-transcript-api` + Claude API
