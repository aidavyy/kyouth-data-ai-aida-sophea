from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Kyouth Week 3 Frontend")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
	return templates.TemplateResponse(
		request=request,
		name="chat_page.html",
		context={
			"title": "Kyouth Week 3 Frontend",
			"message": "Hello World",
		},
	)