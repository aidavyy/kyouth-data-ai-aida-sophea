FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir fastapi jinja2 python-dotenv "uvicorn[standard]>=0.23.0,<1.0.0"

# Install system build dependencies required to compile httptools/uvloop for uvicorn 0.8
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	build-essential \
	gcc \
	g++ \
	autoconf \
	automake \
	libtool \
	python3-dev \
	pkg-config \
	libssl-dev \
	libffi-dev \
	libuv1-dev \
	zlib1g-dev \
	file \
	&& rm -rf /var/lib/apt/lists/*

# Copy backend source files
COPY week3/backend/src ./src

# Copy week2 code so backend can import prompt_model
COPY week2 ./week2

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
