FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY sentinella/ sentinella/
RUN pip install --no-cache-dir .

# Scarica modello spaCy italiano
RUN python -m spacy download it_core_news_sm

COPY . .

EXPOSE 8000
CMD ["uvicorn", "sentinella.main:app", "--host", "0.0.0.0", "--port", "8000"]
