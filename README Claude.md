# 🎙 Voice Agent with RAG + Conversation Memory

A locally hosted AI voice agent that answers questions from your own documents and remembers the full conversation across turns — like a real phone call. Built entirely with open-source tools and free APIs.

---

## Demo Flow

```
You speak → Whisper transcribes → Qdrant searches your PDF → 
Llama 3.3 answers in context → edge-tts speaks the reply → 
You hear the response
```

Multi-turn memory means the agent remembers everything said earlier in the conversation — ask a follow-up and it understands what you're referring to.

---

## Architecture

```
Browser (mic)
    │  POST audio + session_id
    ▼
n8n Webhook
    ├── va-whisper:8001   → speech to text (faster-whisper 1.1)
    ├── va-rag:8003       → semantic search your PDF (Qdrant + sentence-transformers)
    ├── Load History      → load conversation memory (n8n staticData)
    ├── va-llm:8004       → LLM call (OpenRouter → Llama 3.3 70B free)
    ├── Save History      → persist updated conversation
    └── va-tts:8002       → text to speech (edge-tts 7.2.8)
         │
         ▼
    Browser plays MP3 reply
```

---

## Stack

| Layer | Tool | Version | Purpose |
|---|---|---|---|
| Orchestration | [n8n](https://n8n.io) Community | 2.16+ | Workflow engine — glues all services |
| Speech to Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 1.1+ | Transcribes mic audio to text |
| Vector Database | [Qdrant](https://qdrant.tech) | latest | Stores and searches document embeddings |
| Embeddings | [sentence-transformers](https://sbert.net) | 3.3+ | Converts text to vectors (all-MiniLM-L6-v2) |
| LLM | [OpenRouter](https://openrouter.ai) | — | Routes to Llama 3.3 70B (free tier) |
| Text to Speech | [edge-tts](https://github.com/rany2/edge-tts) | 7.2.8+ | Microsoft Edge neural TTS voices |
| API Framework | [FastAPI](https://fastapi.tiangolo.com) | 0.115 | Powers all four local services |
| Containerisation | [Docker Desktop](https://docker.com) | — | Runs all services in isolation |

---

## Features

- **Voice in, voice out** — hold a button, speak, release, hear the AI reply
- **RAG (Retrieval-Augmented Generation)** — answers come from your documents, not general knowledge
- **Conversation memory** — full multi-turn context, like a real phone call
- **Session management** — UUID sessions, 30-minute expiry, "New Conversation" button
- **Runs locally** — everything except the LLM API call stays on your machine
- **Client-ready** — swap the PDF and system prompt per demo, everything else stays the same
- **GitHub ready** — clean structure, .env for secrets, Makefile for all commands

---

## Prerequisites

- macOS (Apple Silicon M1/M2/M3 or Intel)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running
- n8n Community Edition running as a Docker container
- [OpenRouter](https://openrouter.ai) account (free — no credit card required)
- A PDF document to use as your knowledge base

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/voice-agent.git
cd voice-agent
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
WHISPER_MODEL=base
```

### 2. Build and start

```bash
make build
```

First build takes 15–25 minutes (downloads AI models). Subsequent starts take under 30 seconds.

### 3. Connect your existing n8n

```bash
make connect-n8n N8N=your-n8n-container-name
```

To find your n8n container name: `docker ps | grep n8n`

### 4. Load your knowledge document

```bash
make ingest FILE=/path/to/your-document.pdf
```

### 5. Import the n8n workflow

1. Open **http://localhost:5678**
2. Click **⋮** → **Import from File**
3. Select `n8n/workflow.json`
4. The workflow appears with all 8 nodes connected
5. Toggle **Active** to ON

### 6. Start the frontend

```bash
make frontend
```

### 7. Open and speak

Open **http://localhost:3000**, allow microphone access, hold the button and speak.

---

## Project Structure

```
voice-agent/
├── .env.example              # Environment variable template
├── .gitignore                # Keeps secrets and build artifacts out of git
├── Makefile                  # All common commands
├── README.md                 # This file
├── docker-compose.yml        # Defines all 4 AI service containers
│
├── services/
│   ├── whisper/              # Speech-to-text service (port 8001)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── tts/                  # Text-to-speech service (port 8002)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── rag/                  # Document search service (port 8003)
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   └── llm/                  # OpenRouter proxy service (port 8004)
│       ├── Dockerfile
│       ├── main.py
│       └── requirements.txt
│
├── frontend/
│   └── index.html            # Browser UI with mic recording and chat history
│
└── n8n/
    └── workflow.json         # Importable n8n workflow (8 nodes, pre-wired)
```

---

## Service Endpoints

| Service | Container | Local URL | n8n URL | Purpose |
|---|---|---|---|---|
| Whisper STT | `va-whisper` | http://localhost:8001 | http://va-whisper:8001 | Audio → text |
| TTS | `va-tts` | http://localhost:8002 | http://va-tts:8002 | Text → audio |
| RAG API | `va-rag` | http://localhost:8003 | http://va-rag:8003 | Document search |
| LLM Proxy | `va-llm` | http://localhost:8004 | http://va-llm:8004 | OpenRouter call |
| Qdrant DB | `va-qdrant` | http://localhost:6333 | http://va-qdrant:6333 | Vector storage |
| Qdrant UI | — | http://localhost:6333/dashboard | — | Visual browser |
| n8n | your container | http://localhost:5678 | — | Workflow builder |
| Frontend | Python server | http://localhost:3000 | — | Voice agent UI |

---

## Makefile Commands

```bash
make build                        # Build all containers and start
make start                        # Start without rebuilding
make stop                         # Stop all containers
make status                       # Show container status + KB chunk count
make logs                         # Stream all logs live
make logs-va-rag                  # Stream one service's logs

make connect-n8n N8N=<name>       # Connect n8n to voice-agent network
make ingest FILE=/path/to/file    # Ingest a PDF or TXT into knowledge base
make reset-kb                     # Wipe knowledge base
make query Q="your question"      # Test RAG search directly

make frontend                     # Serve UI at localhost:3000
make test-whisper                 # Health check Whisper
make test-tts                     # Generate test audio
make test-rag                     # Health check RAG
```

---

## n8n Workflow — 8 Nodes

```
Webhook → Whisper STT → RAG Query → Load History → 
OpenRouter → Save History → TTS → Respond to Webhook
```

| Node | Type | Purpose |
|---|---|---|
| Webhook | Trigger | Receives audio + session_id from browser |
| Whisper STT | HTTP Request | Sends audio to va-whisper, gets transcript |
| RAG Query | HTTP Request | Searches knowledge base, gets 3 relevant chunks |
| Load History | Code | Reads session memory, serialises history |
| OpenRouter | HTTP Request | Sends to va-llm, gets AI reply |
| Save History | Code | Appends turn to memory, trims to 20 messages |
| TTS | HTTP Request | Converts reply text to MP3 audio |
| Respond to Webhook | Response | Returns MP3 + transcript/reply headers |

---

## Conversation Memory

Sessions are tracked by UUID generated in the browser on page load. The session_id is sent as a URL query parameter with every request (`?session_id=abc-123`).

n8n's `$getWorkflowStaticData('global')` persists conversation history between workflow executions. Each session stores up to 20 messages (10 turns) — older messages are trimmed automatically. Sessions expire after 30 minutes of inactivity.

Click **↺ New conversation** in the UI to start a fresh session.

---

## Customising Per Client Demo

Only two things change between demos:

### 1. Load a different knowledge document

```bash
make reset-kb
make ingest FILE=/path/to/client-document.pdf
```

### 2. Change the system prompt

In n8n → OpenRouter HTTP Request node → update the `system_prompt` field sent in the body. The LLM service prepends it to the knowledge base context automatically.

Example for a bank:
```
You are a helpful banking assistant for NorthStar Bank.
Answer using ONLY the context below. If not found, say:
Please call our support line for assistance.
Keep answers under 3 sentences.
```

---

## Managing the Knowledge Base

```bash
# Add a document
make ingest FILE=/path/to/file.pdf

# Add a second document (appends — doesn't overwrite)
make ingest FILE=/path/to/another.pdf

# Check how many chunks are indexed
make status

# Test what RAG returns for a question
make query Q="what are your branch hours"

# Wipe everything and start fresh
make reset-kb
```

Ingested documents are split into ~400-word overlapping chunks, embedded with `all-MiniLM-L6-v2`, and stored in Qdrant. The RAG service returns the top 3 most semantically similar chunks for each query.

---

## LLM Model Options (OpenRouter free tier)

| Model ID | Quality | Notes |
|---|---|---|
| `meta-llama/llama-3.3-70b-instruct:free` | ⭐⭐⭐⭐⭐ | Recommended — GPT-4 level |
| `mistralai/mistral-small-3.1:free` | ⭐⭐⭐⭐ | Good Mistral alternative |
| `google/gemma-3-12b-it:free` | ⭐⭐⭐ | Fast, lightweight |

Change model by updating `.env`:
```
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

Then: `docker compose restart va-llm`

Free tier limits: 20 requests/minute, 200 requests/day.

---

## TTS Voice Options

Change the `voice` field in the n8n TTS node:

| Voice | Accent | Style |
|---|---|---|
| `en-US-AriaNeural` | American | Female, warm (default) |
| `en-US-GuyNeural` | American | Male, clear |
| `en-GB-SoniaNeural` | British | Female, professional |
| `en-GB-RyanNeural` | British | Male, authoritative |
| `en-AU-NatashaNeural` | Australian | Female, friendly |
| `en-CA-ClaraNeural` | Canadian | Female, neutral |
| `fr-CA-SylvieNeural` | French Canadian | Female |

---

## Troubleshooting

### Docker not running
Open Docker Desktop. Wait for the whale icon in the menu bar to stop animating.

### Port already in use
```bash
docker compose down --remove-orphans
lsof -i :8001 -i :8002 -i :8003 -i :8004 -i :6333
kill -9 $(lsof -ti :8001)   # repeat for other ports if needed
```

### n8n can't reach services
```bash
make connect-n8n N8N=your-n8n-container-name
docker exec your-n8n-container wget -qO- http://va-whisper:8001/health
```

### Knowledge base empty after restart
Qdrant data persists in a Docker volume — it should survive restarts. If empty:
```bash
make status   # check chunks_indexed
make ingest FILE=/path/to/your-document.pdf
```

### Whisper audio error
The browser sends WebM/Opus on Chrome and MP4 on Safari. The Whisper service uses ffmpeg to convert before transcription. If you see conversion errors:
```bash
docker compose logs va-whisper --tail=30
```

### OpenRouter model not found
The free model tier changes. Update `.env` with a current free model ID from https://openrouter.ai/models?q=free and restart: `docker compose restart va-llm`

### TTS says "Equals"
The `text` expression in the TTS n8n node is not in expression mode. Click the field's `{}` toggle to make it blue, then confirm the value is `{{ $('OpenRouter').item.json.reply }}` without a leading `=`.

---

## Security Notes

- `.env` is in `.gitignore` — your OpenRouter API key never reaches GitHub
- All AI processing except the LLM call is fully local
- The LLM service sends transcripts to OpenRouter — review their privacy policy for production use
- For production deployment, add authentication to the n8n webhook

---

## Roadmap Ideas

- [ ] Add a `/clear` endpoint to reset a specific session from the frontend
- [ ] Support multiple knowledge bases with a selector in the UI
- [ ] Add a Notion webhook to auto-ingest updated pages
- [ ] WhatsApp or Slack integration via n8n
- [ ] Swap to a local LLM (Ollama) for fully offline operation

---

## License

MIT — free to use, modify, and deploy.

---

*Built with faster-whisper · Qdrant · sentence-transformers · edge-tts · OpenRouter · n8n · Docker Desktop · macOS*
