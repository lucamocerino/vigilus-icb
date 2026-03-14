FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY sentinella/ sentinella/
RUN pip install --no-cache-dir .

# Scarica modello ONNX classifier a build time
RUN python -c "from sentinella.nlp.classifier import get_classifier; get_classifier()._download_model(); print('ONNX model downloaded')"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "sentinella.main:app", "--host", "0.0.0.0", "--port", "8000"]
