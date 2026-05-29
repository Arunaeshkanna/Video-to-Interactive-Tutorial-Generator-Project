# Video-to-Interactive-Tutorial Generator

A polished Streamlit app that converts a technical video into a structured tutorial with:

- YouTube URL or uploaded video input
- Transcript extraction
- Key-frame extraction
- Lightweight RAG over transcript chunks
- Agent-style analysis pipeline
- Blog/tutorial generation
- Mermaid diagrams
- Markdown export
- Chat with the video
- Quiz generator with self-check answers
- PDF export
- Code, command, package, API, and file extraction
- Flashcards
- Difficulty rewrites
- Multi-language tutorial translation
- Learning path and project ideas
- Interactive Mermaid diagram editor
- Multiple summary formats
- Browser-based voice playback
- History dashboard for generated tutorials

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
```

Add your API key to `.env`:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TRANSCRIBE_MODEL=whisper-large-v3-turbo
```

The UI never asks for or displays API keys.

## Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

## Feature Notes

- Use the sidebar to choose difficulty and target language before generation.
- Most advanced tools are generated on demand from their tabs to save Groq tokens.
- PDF export requires `reportlab`, included in `requirements.txt`.
- Voice playback uses the browser's built-in speech synthesis, so no extra API key is needed.
- History is stored locally under `outputs/history/`.

## Notes

- YouTube videos first try official/available captions through `youtube-transcript-api`.
- If no transcript is available and `GROQ_API_KEY` is configured, uploaded/local media can be transcribed through Groq Whisper.
- Key frames are extracted with OpenCV and saved under `outputs/`.
