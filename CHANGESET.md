# Changeset Log


- 2026-01-05T10:08:10+07:00 34ab84a
  - feat(youtube-analyzer): add YouTube video transcript analyzer with Poe API
  - - Extract transcripts from YouTube videos using youtube-transcript-api v1.x
  - - Analyze with AI via Poe API (OpenAI-compatible endpoint)
  - - Multiple analysis modes: summary, detailed, sentiment, topics, chapters, qa, raw
  - - Preflight check with automatic model fallback (gpt-5.2-pro -> claude-sonnet-4.5)
  - - Whisper fallback for videos without captions
  - - Streaming responses with proper error handling and timeouts
  - Files changed:
    - Added: youtube-analyzer/README.md
    - Added: youtube-analyzer/RESEARCH.md
    - Added: youtube-analyzer/requirements.txt
    - Added: youtube-analyzer/youtube_analyzer.py
