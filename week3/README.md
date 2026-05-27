# Week 3

Run the backend and frontend together with Docker Compose:

```bash
docker compose -f docker-compose.yml up --build
```

To run the frontend by itself, go into the frontend folder first and start it with Uvicorn:

```bash
cd frontend
uv sync
uv run uvicorn --app-dir src main:app --reload
```

To build and run the frontend container:

```bash
cd frontend
docker build -t week3-frontend .
docker run --rm -p 8000:8000 week3-frontend
```

