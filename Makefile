# ── Voice Agent Makefile ──────────────────────────────────────────
# Usage: make <target>

.PHONY: start stop restart status logs build \
        connect-n8n ingest status reset-kb \
        frontend test-whisper test-tts test-rag help

# ── Docker lifecycle ─────────────────────────────────────────────

start:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose restart

build:
	docker compose up -d --build

status:
	@echo "\n── Docker services ──"
	@docker compose ps
	@echo "\n── Knowledge base ──"
	@curl -s http://localhost:8003/health | python3 -m json.tool

logs:
	docker compose logs -f

logs-%:
	docker compose logs -f $*

# ── n8n network bridge ───────────────────────────────────────────

connect-n8n:
	@if [ -z "$(N8N)" ]; then \
		echo "Usage: make connect-n8n N8N=your-n8n-container-name"; \
		exit 1; \
	fi
	docker network connect voice-agent_default $(N8N)
	@echo "Connected $(N8N) to voice-agent_default"
	@echo "Testing connection..."
	@docker exec $(N8N) wget -qO- http://va-whisper:8001/health 2>&1 || \
		echo "Connection test failed — check container name"

# ── Knowledge base management ────────────────────────────────────

ingest:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make ingest FILE=/path/to/document.pdf"; \
		exit 1; \
	fi
	curl -X POST http://localhost:8003/ingest -F "file=@$(FILE)"
	@echo ""

reset-kb:
	curl -X DELETE http://localhost:8003/reset
	@echo ""

query:
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make query Q=\"your test question\""; \
		exit 1; \
	fi
	curl -s -X POST http://localhost:8003/query \
		-H "Content-Type: application/json" \
		-d "{\"query\": \"$(Q)\", \"n_results\": 3}" | python3 -m json.tool

# ── Frontend ─────────────────────────────────────────────────────

frontend:
	@echo "Starting frontend at http://localhost:3000"
	@echo "Press Ctrl+C to stop"
	cd frontend && python3 -m http.server 3000

# ── Health checks ────────────────────────────────────────────────

test-whisper:
	curl -s http://localhost:8001/health | python3 -m json.tool

test-tts:
	curl -s -X POST http://localhost:8002/synthesize \
		-H "Content-Type: application/json" \
		-d '{"text": "Voice agent is working correctly."}' \
		--output /tmp/test-voice.mp3 && \
		echo "Audio saved to /tmp/test-voice.mp3 — open it to listen"

test-rag:
	curl -s http://localhost:8003/health | python3 -m json.tool

test-qdrant:
	curl -s http://localhost:6333/healthz

# ── Help ─────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Voice Agent — available commands:"
	@echo ""
	@echo "  make build                   Build and start all services"
	@echo "  make start                   Start services (no rebuild)"
	@echo "  make stop                    Stop all services"
	@echo "  make status                  Show service status + KB stats"
	@echo "  make logs                    Stream all logs"
	@echo "  make logs-va-rag             Stream one service's logs"
	@echo ""
	@echo "  make connect-n8n N8N=<name>  Connect n8n to this network"
	@echo ""
	@echo "  make ingest FILE=<path>      Ingest a PDF or TXT file"
	@echo "  make reset-kb                Wipe knowledge base"
	@echo "  make query Q=\"question\"      Test RAG search directly"
	@echo ""
	@echo "  make frontend                Serve frontend at localhost:3000"
	@echo ""
	@echo "  make test-whisper            Health check Whisper"
	@echo "  make test-tts                Generate test audio"
	@echo "  make test-rag                Health check RAG"
	@echo ""
