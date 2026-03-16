"""Classificatore semantico per notizie italiane.

Usa ONNX Runtime con modello quantizzato int8 per classificare
articoli nelle dimensioni di sicurezza tramite cosine similarity.

L'inferenza ONNX gira in un subprocess separato così la memoria
viene rilasciata completamente dal SO al termine.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tarfile
import threading
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

DIMENSIONS = [
    "geopolitica",
    "terrorismo",
    "cyber",
    "eversione",
    "militare",
    "sociale",
    "non_pertinente",
]

# Descrizioni ricche per ogni dimensione
DIMENSION_DESCRIPTIONS: dict[str, list[str]] = {
    "geopolitica": [
        "relazioni internazionali diplomazia trattati sanzioni politica estera",
        "NATO Unione Europea UE summit bilaterale ambasciata alleanza",
        "conflitto geopolitico crisi diplomatica negoziati pace guerra",
        "Ucraina Russia Cina Medio Oriente Iran Turchia tensioni internazionali",
        "G7 G20 ONU Consiglio di Sicurezza vertice internazionale",
    ],
    "terrorismo": [
        "attentato terroristico bomba esplosione strage kamikaze jihad",
        "terrorismo ISIS Al-Qaeda cellula terroristica radicalizzazione",
        "minaccia terroristica allarme attacco armato sequestro ostaggio",
        "antiterrorismo intelligence servizi segreti indagine terrorismo",
        "foreign fighter lupo solitario attentatore estremismo islamico",
    ],
    "cyber": [
        "attacco informatico hacker ransomware malware phishing cybersecurity",
        "data breach violazione dati vulnerabilità CVE exploit zero-day",
        "CSIRT ACN agenzia cybersicurezza nazionale infrastruttura critica",
        "sicurezza informatica rete difesa cyber spionaggio digitale",
        "DDoS botnet trojan crimine informatico dark web furto dati",
    ],
    "eversione": [
        "estremismo politico neofascismo anarchismo eversione sovversivo",
        "estrema destra estrema sinistra movimenti eversivi insurrezione",
        "black bloc rivolta violenza politica organizzazione eversiva",
        "radicalismo politico complotto golpe piano sovversivo cellula",
        "propaganda estremista odio razziale suprematismo antisemitismo",
    ],
    "militare": [
        "esercito marina militare aeronautica forze armate difesa nazionale",
        "esercitazione militare missione operazione base militare NATO",
        "Aviano Sigonella Ghedi caccia F-35 mezzi militari dispiegamento",
        "carabinieri guardia di finanza operazione militare pattugliamento",
        "armi armamenti sommergibile portaerei droni militari flotta",
    ],
    "sociale": [
        "sciopero manifestazione protesta tensione sociale disordini piazza",
        "criminalità mafia camorra ndrangheta omicidio rapina arresto",
        "cronaca nera incidente emergenza sanitaria disastro naturale",
        "economia crisi inflazione disoccupazione lavoro welfare povertà",
        "immigrazione migranti sbarchi accoglienza integrazione frontiera",
    ],
    "non_pertinente": [
        "gossip spettacolo celebrity vip televisione reality show intrattenimento",
        "sport calcio serie A campionato partita gol classifica pallone",
        "moda fashion tendenze lifestyle cucina ricette viaggio turismo",
        "oroscopo meteo previsioni tempo curiosità animali natura",
        "musica cinema festival concerto attore cantante artista album",
    ],
}

RELEVANCE_THRESHOLD = 0.25

KEYWORD_OVERRIDES: dict[str, list[str]] = {
    "terrorismo": [
        "terrorismo", "terrorista", "attentato", "isis", "jihad",
        "kamikaze", "al-qaeda", "al qaeda",
    ],
    "cyber": [
        "cyber", "hacker", "ransomware", "malware", "phishing",
        "data breach", "csirt", "vulnerabilità", "cve-",
    ],
}

MODEL_RELEASE_URL = (
    "https://github.com/lucamocerino/vigilus-icb/releases/download/"
    "v1.1.0-model/classifier-onnx-v1.tar.gz"
)
MODEL_DIR = Path(__file__).parent / "model"


class ClassificationResult(TypedDict):
    dimension: str
    confidence: float
    method: str  # "semantic" | "keyword" | "fallback"


_lock = threading.Lock()
_instance: SmartClassifier | None = None
_tfidf: Any = None


def get_classifier() -> SmartClassifier:
    """Restituisce il singleton del classificatore (lazy init thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SmartClassifier()
    return _instance


def _get_tfidf():
    """Restituisce il singleton TF-IDF (lazy, ~2MB)."""
    global _tfidf
    if _tfidf is None:
        with _lock:
            if _tfidf is None:
                from sentinella.nlp.tfidf_classifier import TfidfLiteClassifier
                _tfidf = TfidfLiteClassifier(DIMENSION_DESCRIPTIONS)
    return _tfidf


# ── Script eseguito nel subprocess per l'inferenza ONNX ──────────────

_SUBPROCESS_SCRIPT = r'''
import json, sys, numpy as np

def main():
    input_data = json.loads(sys.stdin.read())
    texts = input_data["texts"]
    dim_descs = input_data["dim_descs"]
    threshold = input_data["threshold"]
    model_dir = input_data["model_dir"]

    import onnxruntime as ort
    from tokenizers import Tokenizer

    session = ort.InferenceSession(
        f"{model_dir}/model_quantized.onnx",
        providers=["CPUExecutionProvider"],
    )
    tokenizer = Tokenizer.from_file(f"{model_dir}/tokenizer.json")
    tokenizer.enable_padding()
    tokenizer.enable_truncation(max_length=128)

    def encode(txts):
        encoded = tokenizer.encode_batch(txts)
        ids = np.array([e.ids for e in encoded], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        tids = np.array([e.type_ids for e in encoded], dtype=np.int64)
        out = session.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": tids})
        hidden = out[0]
        mask_exp = mask[:, :, np.newaxis].astype(np.float32)
        pooled = (hidden * mask_exp).sum(axis=1) / mask_exp.sum(axis=1)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        return pooled / norms

    # Compute dimension embeddings
    dim_names = list(dim_descs.keys())
    dim_embs = {}
    for dim, descs in dim_descs.items():
        embs = encode(descs)
        mean_emb = np.mean(embs, axis=0)
        norm = np.linalg.norm(mean_emb)
        if norm > 0:
            mean_emb /= norm
        dim_embs[dim] = mean_emb

    dim_matrix = np.array([dim_embs[d] for d in dim_names])

    # Classify texts
    text_embs = encode(texts)
    sim_matrix = text_embs @ dim_matrix.T

    non_pert_idx = dim_names.index("non_pertinente") if "non_pertinente" in dim_names else -1
    results = []
    for i in range(len(texts)):
        scores = sim_matrix[i]
        best_score, best_dim = -1.0, "non_pertinente"
        for j, dim in enumerate(dim_names):
            if dim != "non_pertinente" and scores[j] > best_score:
                best_score = float(scores[j])
                best_dim = dim
        non_pert_score = float(scores[non_pert_idx]) if non_pert_idx >= 0 else 0.0
        if best_score < threshold or non_pert_score > best_score:
            results.append({"dimension": "non_pertinente",
                            "confidence": round(max(non_pert_score, 1.0 - best_score), 3),
                            "method": "semantic"})
        else:
            results.append({"dimension": best_dim,
                            "confidence": round(best_score, 3),
                            "method": "semantic"})

    json.dump(results, sys.stdout)

main()
'''


class SmartClassifier:
    """Classificatore semantico — inferenza ONNX in subprocess per zero memory leak."""

    def __init__(self) -> None:
        pass

    def _download_model(self) -> bool:
        """Scarica il modello ONNX da GitHub Releases se non presente."""
        model_path = MODEL_DIR / "model_quantized.onnx"
        if model_path.exists():
            return True
        try:
            import urllib.request
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            tarball = MODEL_DIR / "model.tar.gz"
            logger.info("[classifier] Download modello ONNX da GitHub Releases …")
            urllib.request.urlretrieve(MODEL_RELEASE_URL, tarball)
            with tarfile.open(tarball, "r:gz") as tar:
                tar.extractall(MODEL_DIR)
            tarball.unlink()
            logger.info("[classifier] Modello scaricato in %s", MODEL_DIR)
            return True
        except Exception as e:
            logger.warning("[classifier] Download modello fallito: %s", e)
            return False

    def _run_onnx_subprocess(self, texts: list[str]) -> list[ClassificationResult] | None:
        """Esegue classificazione ONNX in un subprocess separato."""
        try:
            input_data = json.dumps({
                "texts": texts,
                "dim_descs": DIMENSION_DESCRIPTIONS,
                "threshold": RELEVANCE_THRESHOLD,
                "model_dir": str(MODEL_DIR),
            })
            result = subprocess.run(
                [sys.executable, "-c", _SUBPROCESS_SCRIPT],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning("[classifier] Subprocess fallito: %s", result.stderr[:500])
                return None
            return json.loads(result.stdout)
        except Exception as e:
            logger.warning("[classifier] Errore subprocess: %s", e)
            return None

    def classify(self, text: str, feed_category: str = "") -> ClassificationResult:
        """Classifica un singolo articolo."""
        from sentinella.config import settings

        text_lower = text.lower()
        for dim, keywords in KEYWORD_OVERRIDES.items():
            for kw in keywords:
                pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                if re.search(pattern, text_lower):
                    return ClassificationResult(dimension=dim, confidence=0.95, method="keyword")

        if settings.nlp_mode == "full" and self._download_model():
            results = self._run_onnx_subprocess([text])
            if results:
                return results[0]

        # Modalità lite: TF-IDF in-process
        tfidf = _get_tfidf()
        dim, conf = tfidf.classify(text)
        return ClassificationResult(dimension=dim, confidence=conf, method="tfidf")

    def classify_batch(self, texts: list[str], feed_categories: list[str] | None = None) -> list[ClassificationResult]:
        """Classifica un batch di articoli."""
        from sentinella.config import settings

        if feed_categories is None:
            feed_categories = [""] * len(texts)

        results: list[ClassificationResult] = [None] * len(texts)  # type: ignore
        semantic_indices: list[int] = []
        semantic_texts: list[str] = []

        for i, text in enumerate(texts):
            text_lower = text.lower()
            matched = False
            for dim, keywords in KEYWORD_OVERRIDES.items():
                for kw in keywords:
                    pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                    if re.search(pattern, text_lower):
                        results[i] = ClassificationResult(dimension=dim, confidence=0.95, method="keyword")
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                semantic_indices.append(i)
                semantic_texts.append(text)

        # In modalità "lite" skip ONNX subprocess per risparmiare ~250MB
        use_onnx = settings.nlp_mode == "full"

        if use_onnx and semantic_texts and self._download_model():
            semantic_results = self._run_onnx_subprocess(semantic_texts)
            if semantic_results:
                for idx, result in zip(semantic_indices, semantic_results):
                    results[idx] = result
            else:
                for idx in semantic_indices:
                    results[idx] = self._classify_fallback(texts[idx].lower(), feed_categories[idx])
        elif semantic_texts:
            # Modalità lite: TF-IDF in-process
            tfidf = _get_tfidf()
            tfidf_results = tfidf.classify_batch(semantic_texts)
            for idx, (dim, conf) in zip(semantic_indices, tfidf_results):
                results[idx] = ClassificationResult(dimension=dim, confidence=conf, method="tfidf")
        else:
            for idx in semantic_indices:
                if results[idx] is None:
                    results[idx] = self._classify_fallback(texts[idx].lower(), feed_categories[idx])

        return results

    @staticmethod
    def _classify_fallback(text_lower: str, feed_category: str) -> ClassificationResult:
        """Fallback keyword legacy se il modello non è disponibile."""
        from sentinella.collectors.mega_rss import DIMENSION_KEYWORDS, CATEGORY_DIMENSION

        for dim, keywords in DIMENSION_KEYWORDS.items():
            for kw in keywords:
                pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                if re.search(pattern, text_lower):
                    return ClassificationResult(dimension=dim, confidence=0.5, method="fallback")
        # Se nessun keyword matcha, è non pertinente (non assegnare categoria di default)
        dim = CATEGORY_DIMENSION.get(feed_category)
        if dim and feed_category in ("difesa", "cyber", "geopolitica"):
            return ClassificationResult(dimension=dim, confidence=0.3, method="fallback")
        return ClassificationResult(dimension="non_pertinente", confidence=0.2, method="fallback")
