from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv(BASE_DIR.parent / '.env')
BACKEND_URL = os.getenv("BACKEND_URL", "")

app = FastAPI(title="Kyouth Week 3 Frontend")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	return templates.TemplateResponse(
		request=request,
		name="chat_page.html",
		context={
			"title": "Resume Helper Chatbot",
			"message": "Welcome to the Resume Helper",
			"backend_url": BACKEND_URL,
		},
	)