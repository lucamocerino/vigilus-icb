FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU-only (molto più leggero, ~200MB vs ~2GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml .
COPY sentinella/ sentinella/
RUN pip install --no-cache-dir .

# Scarica modelli NLP a build time
RUN python -m spacy download it_core_news_sm
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "sentinella.main:app", "--host", "0.0.0.0", "--port", "8000"]
