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

- 2026-01-05T11:13:19+07:00 7331b5b
  - docs: add comprehensive analysis modes documentation and ERC3 seed document
  - Update README with detailed mode explanations and examples
  - Fix installation path and add venv setup instructions
  - Add ERC3 Agent Architecture seed document with:
    - 7 architectural patterns (dynamic prompts, context builder, validators)
    - Solution evolution timeline (V1-V6)
    - Keywords and terminology glossary
    - Development roadmap with priorities
    - Enterprise considerations (security, cost, compliance)
  - Add architecture diagrams (agent flow, evolution, multi-agent)
  - Files changed:
    - Modified: README.md
    - Added: docs/ERC3_AGENT_ARCHITECTURE_SEED.md
    - Added: docs/diagrams/agent-architecture.png
    - Added: docs/diagrams/multi-agent-orchestration.png
    - Added: docs/diagrams/solution-evolution.png

- 2026-01-05T12:30:00+07:00 9e2c0ff
  - feat: add seed mode for comprehensive architecture document generation
  - Add 'seed' mode that generates structured development seed documents
  - Includes 8 sections: executive summary, architectural patterns, insights,
    terminology, implementation recommendations, evolution, roadmap, resources
  - Uses higher max_tokens (8192) for comprehensive output
  - Files changed:
    - Modified: youtube_analyzer.py
    - Modified: README.md
    - Modified: ARCHITECTURE.md

- 2026-01-05T13:15:00+07:00 6e9face
  - fix: add dynamic timeouts for reasoning models and update fallback
  - Change fallback model from claude-sonnet-4.5 to claude-opus-4.5
  - Add REASONING_MODELS set with GPT-5.x reasoning variants
  - Increase timeout from 60s to 600s (10 min) for reasoning models
  - Add user notification when using reasoning models
  - Add ERC3_SEED_GENERATED.md generated via seed mode API
  - Files changed:
    - Modified: youtube_analyzer.py
    - Modified: README.md
    - Added: docs/ERC3_SEED_GENERATED.md
