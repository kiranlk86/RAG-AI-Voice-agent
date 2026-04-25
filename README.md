# Voice Agent with RAG + Conversation Memory

A locally hosted AI voice agent that answers questions from your own documents
and remembers the conversation context across turns — like a phone call.

## Stack

| Component | Role | Version |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Speech → Text | 1.1+ |
| [Qdrant](https://qdrant.tech) | Vector database (RAG) | latest |
| [sentence-transformers](https://sbert.net) | Document embeddings | 3.3+ |
| [edge-tts](https://github.com/rany2/edge-tts) | Text → Speech | 7.2.8+ |
| [OpenRouter](https://openrouter.ai) | LLM API (Mistral 7B free) | — |
| [n8n](https://n8n.io) | Workflow orchestration | community |

## Prerequisites

- macOS with Docker Desktop installed and running
- n8n Community Edition running as a Docker container
- OpenRouter account (free) — [openrouter.ai](https://openrouter.ai)

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_USERNAME/voice-agent.git
cd voice-agent
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 2. Start services
make start

# 3. Connect your existing n8n
make connect-n8n N8N=your-n8n-container-name

# 4. Import n8n workflow
# Open http://localhost:5678 → ⋮ menu → Import from File → select n8n/workflow.json
# Then update the OpenRouter API key inside the workflow

# 5. Load your knowledge document
make ingest FILE=/path/to/your-document.pdf

# 6. Serve the frontend
make frontend

# 7. Open http://localhost:3000 and start talking
```

## Architecture
## Managing the Knowledge Base

```bash
make ingest FILE=/path/to/document.pdf   # add a document
make status                               # check chunk count
make reset-kb                             # wipe and start fresh
```

## License

MIT
