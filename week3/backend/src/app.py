from pathlib import Path
import sys
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

week2_paths = [
	Path(__file__).resolve().parent.parent.parent.parent / "week2", # For when running from backend/
	Path(__file__).resolve().parent.parent.parent / "week2", # For when running from backend/src/
	Path(__file__).resolve().parent.parent / "week2", # For when running from backend/src/app.py
]
for week2_path in week2_paths:
	if week2_path.exists() and str(week2_path) not in sys.path:
		sys.path.insert(0, str(week2_path))
		break

from prompt_model import prompt_model

load_dotenv()

# Default model to use (can be overridden via environment variable)
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama3.1")

app = FastAPI(title="Kyouth Week 3 Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
	message: str
	pdf_text: str = ""


class ChatResponse(BaseModel):
	reply: str


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
	html = """<!doctype html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>Kyouth Week 3</title>
</head>
<body>
	<main>
		<h1>Kyouth Week 3</h1>
		<p>Backend template is ready.</p>
	</main>
</body>
</html>"""
	return HTMLResponse(html)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
	"""Process user message and optional PDF text through the LLM."""
	# Combine the message and PDF text for the prompt
	combined_input = req.message
	if req.pdf_text:
		combined_input = f"Resume/Context:\n{req.pdf_text}\n\nUser Question:\n{req.message}"
	
	# Call the LLM via week2's prompt_model function
	response = prompt_model(DEFAULT_MODEL, combined_input)
	
	return ChatResponse(reply=response)