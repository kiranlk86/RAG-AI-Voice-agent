# ── Voice Agent Makefile ────────────────────────────────────────────
# One-command GitHub operations + Docker lifecycle
#
# Usage:
#   make push       Stage all, commit with message, push to origin
#   make release    Push + create GitHub release with auto-generated notes
#   make license    Ensure MIT LICENSE file is present
#   make status     Show git status + remote info + Docker containers
#   make all        Build + start + status
#   make help       Show this help

# ── Docker targets (original) ──────────────────────────────────────
.PHONY: start stop restart docker-build docker-status logs build \
        connect-n8n ingest reset-kb query frontend \
        test-whisper test-tts test-rag test-qdrant help

# ── GitHub targets ─────────────────────────────────────────────────
.PHONY: push release license gh-status

REMOTE   ?= origin
BRANCH   ?= main
MESSAGE  ?= Update: $(shell date +%Y-%m-%d) — $(m)

## Stage all changes, commit, and push
push:
	@git add -A
	@git diff --cached --quiet && echo "Nothing to commit." || \
		git commit -m "chore: $(MESSAGE)"
	git push $(REMOTE) $(BRANCH)
	@echo "✅ Pushed to $(REMOTE)/$(BRANCH)"

## Push and create a GitHub release
release: push
	@TAG=$$(git describe --tags --abbrev=0 2>/dev/null || echo ""); \
	if [ -z "$$TAG" ]; then \
		echo "No existing tags. Creating v0.1.0"; \
		TAG="v0.1.0"; \
	else \
		MAJOR=$$(echo $$TAG | cut -d. -f1 | tr -d 'v'); \
		MINOR=$$(echo $$TAG | cut -d. -f2); \
		PATCH=$$(echo $$TAG | cut -d. -f3); \
		PATCH=$$((PATCH + 1)); \
		TAG="v$$MAJOR.$$MINOR.$$PATCH"; \
		echo "Bumping tag: $$TAG"; \
	fi; \
	git tag $$TAG && git push $(REMOTE) $$TAG; \
	gh release create $$TAG \
		--repo kiranklabs/RAG-AI-Voice-agent \
		--generate-notes \
		--title "Voice Agent $$TAG"; \
	"✅ Released $$TAG"

## Ensure LICENSE file exists
license:
	@test -f LICENSE && echo "✅ LICENSE already exists" || \
		(echo "Adding MIT LICENSE..." && curl -sL https://www.mit.edu/~mdillon/website/licenses/mit-license.txt -o LICENSE && echo "✅ LICENSE added")

## Show repo status + Docker status
status:
	@echo "── Git Status ──"
	@git status -s
	@echo ""
	@echo "── Remote ──"
	@git remote -v
	@echo ""
	@echo "── Latest Commits ──"
	@git log --oneline -5
	@echo ""
	@echo "── Docker Services ──"
	@docker compose ps 2>/dev/null || echo "Docker not running"

# ── Docker lifecycle ─────────────────────────────────────────────

build:
	docker compose up -d --build

start:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose restart

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
	@echo "  GitHub:"
	@echo "    make push          Stage all, commit, push to origin"
	@echo "    make push m='msg'  Push with custom commit message"
	@echo "    make release       Push + create GitHub release (auto-bump)"
	@echo "    make status        Git status + Docker status"
	@echo ""
	@echo "  Docker:"
	@echo "    make build         Build all containers and start"
	@echo "    make start         Start without rebuilding"
	@echo "    make stop          Stop all containers"
	@echo "    make status        Show container status"
	@echo "    make logs          Stream all logs"
	@echo "    make logs-va-rag   Stream one service's logs"
	@echo ""
	@echo "  Knowledge base:"
	@echo "    make ingest FILE=<path>      Ingest a PDF or TXT"
	@echo "    make reset-kb                Wipe knowledge base"
	@echo "    make query Q=\"question\"      Test RAG directly"
	@echo ""
	@echo "  Other:"
	@echo "    make connect-n8n N8N=<name>  Bridge n8n to network"
	@echo "    make frontend                Serve UI at localhost:3000"
	@echo "    make test-whisper            Health check Whisper"
	@echo "    make test-tts                Generate test audio"
	@echo "    make test-rag                Health check RAG"
	@echo ""
