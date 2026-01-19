FROM python:3.11-slim

RUN apt update && apt install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv pip install --system

COPY . .

CMD ["python", "bot.py"]
