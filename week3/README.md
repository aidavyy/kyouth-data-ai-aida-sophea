# Week 3

## Project Overview

Week 3 is a full-stack resume helper chat application with a FastAPI backend, a FastAPI/Jinja frontend, and LLM integration reused from Week 2. The frontend lets a user type a message, optionally upload a PDF resume, and send both pieces of context to the backend. The backend combines the inputs and routes them through `week2/prompt_model.py`, which can call either a local Ollama model or a Gemini model depending on configuration.

## Project Structure

```text
week3/
	docker-compose.yml
	README.md
	.env.example
	backend/
		Dockerfile
		pyproject.toml
		src/app.py
	frontend/
		Dockerfile
		pyproject.toml
		src/main.py
		src/templates/chat_page.html
```

- `docker-compose.yml`: runs the backend and frontend together.
- `backend/src/app.py`: exposes the chat API and the backend HTML endpoint.
- `frontend/src/main.py`: serves the frontend page and passes the backend URL into the template.
- `frontend/src/templates/chat_page.html`: contains the browser UI, PDF upload control, and chat request logic.
- `week2/prompt_model.py`: provides the model call used by the backend.

The backend also depends on `week2/prompt_model.py` for model calls, so Week 2 remains part of the runtime architecture even though the Week 3 services are containerized separately.

## Setup Instructions

### Prerequisites

- Docker
- Docker Compose
- Optional for manual runs: `uv`
- Optional for local Ollama inference: a running Ollama server

### Docker Compose

Run both services together from the `week3` folder:

```bash
docker compose -f docker-compose.yml up --build
```

This starts the backend on `http://localhost:8000` and the frontend on `http://127.0.0.1:3000/`.

### Manual Setup With `uv`

Backend:

```bash
cd week3/backend
uv sync
uv run uvicorn src.app:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd week3/frontend
uv sync
$env:BACKEND_URL="http://127.0.0.1:8000"
uv run uvicorn --app-dir src main:app --host 0.0.0.0 --port 3000
```

If you run the backend manually and want local Ollama access, make sure `LLM_MODEL` and `OLLAMA_URL` point to a working model server. For a local Ollama install, use `http://127.0.0.1:11434`. The Docker Compose setup overrides this to `http://host.docker.internal:11434` for the containerized backend. If you use a Gemini model, set `GOOGLE_API_KEY` in your environment before starting the backend.

### Environment Variables

Week 3 uses service-specific `.env` files at runtime:

- `backend/.env` for the backend service
- `frontend/.env` for the frontend service

You can use [.env.example](.env.example) as a reference, but the live values should go in those `.env` files before launching the app. If you run the services with Docker Compose, the backend already gets a Docker-specific `OLLAMA_URL` from `docker-compose.yml`.

- `BACKEND_URL`: URL used by the frontend browser code to call the backend API.
- `LLM_MODEL`: Model name passed to `prompt_model.py`.
- `OLLAMA_URL`: Base URL for a local Ollama server.
- `GOOGLE_API_KEY`: Optional key for Gemini-based prompts.

Do not commit real secrets to the repository.

## Usage

1. Start the services with Docker Compose or run the backend and frontend manually.
2. Open the frontend in your browser at `http://127.0.0.1:3000/`.
3. Type a message and, if needed, upload a PDF resume.
4. Submit the form and wait for the chatbot response to appear in the chat history.

Expected behavior:

- Text-only message: the backend receives `{ "message": "...", "pdf_text": "" }`.
- Message plus PDF: the frontend extracts text from the PDF, sends it as `pdf_text`, and the backend adds it to the prompt.
- Response: the bot returns a JSON payload with a `reply` field and the UI renders it in the chat window.

## API / Function Reference

### Backend

- `GET /health`: returns `{"status": "ok"}` for a simple health check.
- `GET /`: returns a small HTML placeholder from the backend app.
- `POST /chat`: accepts JSON with `message` and `pdf_text` fields and returns `{ "reply": "..." }`.

Example request:

```json
{
	"message": "Summarize this resume for a data analyst role.",
	"pdf_text": "Education: ... Experience: ..."
}
```

Example response:

```json
{
	"reply": "Based on the resume, the candidate has ..."
}
```

The backend combines the user message and optional PDF text, then calls `prompt_model(DEFAULT_MODEL, combined_input)` from Week 2.

### Frontend

- `home()` in `frontend/src/main.py`: renders `chat_page.html` and injects `backend_url` into the template.
- `appendMessage(content, role)` in `chat_page.html`: appends user or bot messages to the visible chat history.
- The form submit handler in `chat_page.html`: reads the text box, extracts PDF text when a file is uploaded, sends the POST request to `/chat`, and renders the reply.
- The PDF upload branch in the submit handler is responsible for reading the uploaded file before the request is sent.

### Service Interaction

The frontend page is served by the frontend container, but the browser sends chat requests directly to the backend URL injected into the page. In Docker Compose, both services are exposed on the host so the browser can reach the backend at `http://localhost:8000` while the UI is open at `http://localhost:3000`.

## Data / Assumptions

- The frontend sends JSON with two fields: `message` and `pdf_text`.
- The PDF is treated as plain extracted text, not as a structured document.
- Large PDFs may exceed practical prompt size limits, so the app works best with short resumes or excerpts.
- The chatbot does not persist chat history; every request is stateless.
- Week 2 prompt routing is reused as-is, so model quality depends on the configured Ollama or Gemini backend.

## Testing

I validated the system with the following checks:

- Frontend: opened the chat page, sent a text message, uploaded a PDF, and confirmed the conversation appeared in the chat history.
- Backend: called `POST /chat` with `curl` or an API client and verified the JSON response shape.
- Integration: confirmed the browser could reach the backend through the Docker Compose port mappings.

To reproduce the backend test:

```bash
curl -X POST http://localhost:8000/chat ^
	-H "Content-Type: application/json" ^
	-d "{\"message\":\"Hello\",\"pdf_text\":\"\"}"
```

## Limitations

- The app does not include authentication or user accounts.
- Chat history is only kept in the browser session and is not stored in a database.
- PDF extraction is basic and may lose formatting or fail on complex files.
- Response quality depends on the selected model and the availability of Ollama or Gemini.
- Very large documents or very long prompts are not handled robustly.

## Architecture Reflection

### Design Choices

The project uses separate frontend and backend services so the UI can stay simple while the backend owns model orchestration and prompt handling. Containerizing each service makes local deployment repeatable and keeps the runtime boundaries clear.

### Trade-offs

I prioritized straightforward deployment with Docker Compose over advanced application structure. The chat UI is intentionally minimal, and the backend reuses the Week 2 model wrapper instead of introducing a new service layer or database.

### Improvements

If I had more time, I would move the frontend to a richer framework, add persistent storage for chat history, add stronger PDF parsing and validation, and deploy the app to a cloud environment with separate runtime configuration for each service.
