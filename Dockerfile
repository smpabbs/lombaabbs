FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN mkdir -p data/media
VOLUME ["/app/data"]

CMD ["python", "-m", "app"]
