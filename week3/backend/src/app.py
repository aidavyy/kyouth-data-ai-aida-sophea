from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Kyouth Week 3 Backend")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	return templates.TemplateResponse(
		"chat_page.html",
		{"request": request, "title": "Kyouth Week 3"},
	)

