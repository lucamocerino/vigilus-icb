"""Classificatore semantico per notizie italiane.

Usa ONNX Runtime con modello quantizzato int8 per classificare
articoli nelle dimensioni di sicurezza tramite cosine similarity.
Nessuna dipendenza da PyTorch a runtime.
"""

from __future__ import annotations

import logging
import os
import re
import tarfile
import threading
from pathlib import Path
from typing import TypedDict

import numpy as np

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

# Descrizioni ricche per ogni dimensione — il modello confronta
# l'embedding dell'articolo con queste descrizioni di riferimento.
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

# URL del modello ONNX quantizzato su GitHub Releases
MODEL_RELEASE_URL = (
    "https://github.com/lucamocerino/vigilus-icb/releases/download/"
    "v1.1.0-model/classifier-onnx-v1.tar.gz"
)
MODEL_DIR = Path(__file__).parent / "model"


class ClassificationResult(TypedDict):
    dimension: str
    confidence: float
    method: str  # "semantic" | "keyword" | "fallback"


# ── Singleton classifier ──────────────────────────────────────────────

_lock = threading.Lock()
_instance: SmartClassifier | None = None


def get_classifier() -> SmartClassifier:
    """Restituisce il singleton del classificatore (lazy init thread-safe)."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = SmartClassifier()
    return _instance


class SmartClassifier:
    """Classificatore semantico ONNX — carica/scarica modello on-demand per risparmiare RAM."""

    def __init__(self) -> None:
        self._session = None
        self._tokenizer = None
        self._dim_embeddings: dict[str, np.ndarray] | None = None
        self._dim_embeddings_cached: dict[str, np.ndarray] | None = None

    # ── Model download + loading ────────────────────────────────────

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

    def _load(self) -> bool:
        """Carica modello ONNX in memoria."""
        try:
            if not self._download_model():
                return False

            import onnxruntime as ort
            from tokenizers import Tokenizer

            logger.info("[classifier] Caricamento modello ONNX …")
            self._session = ort.InferenceSession(
                str(MODEL_DIR / "model_quantized.onnx"),
                providers=["CPUExecutionProvider"],
            )
            self._tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
            self._tokenizer.enable_padding()
            self._tokenizer.enable_truncation(max_length=128)

            # Calcola embedding dimensioni (o usa cache)
            if self._dim_embeddings_cached is None:
                self._dim_embeddings = {}
                for dim, descriptions in DIMENSION_DESCRIPTIONS.items():
                    embs = self._encode(descriptions)
                    self._dim_embeddings[dim] = np.mean(embs, axis=0)
                    norm = np.linalg.norm(self._dim_embeddings[dim])
                    if norm > 0:
                        self._dim_embeddings[dim] /= norm
                # Cache: sono solo 7 x 384 floats = ~10KB
                self._dim_embeddings_cached = dict(self._dim_embeddings)
            else:
                self._dim_embeddings = self._dim_embeddings_cached

            logger.info("[classifier] Modello ONNX pronto")
            return True
        except Exception as e:
            logger.warning("[classifier] Impossibile caricare il modello: %s", e)
            return False

    def _unload(self) -> None:
        """Rilascia modello ONNX dalla memoria."""
        self._session = None
        self._tokenizer = None
        import gc
        gc.collect()
        logger.info("[classifier] Modello ONNX rilasciato dalla memoria")

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode testi con ONNX Runtime (mean pooling + normalize)."""
        assert self._session is not None and self._tokenizer is not None

        encoded = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        token_type_ids = np.array([e.type_ids for e in encoded], dtype=np.int64)

        outputs = self._session.run(None, {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        })

        hidden = outputs[0]  # (batch, seq, hidden_dim)
        mask_exp = attention_mask[:, :, np.newaxis].astype(np.float32)
        pooled = (hidden * mask_exp).sum(axis=1) / mask_exp.sum(axis=1)
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        return pooled / norms

    # ── Classificazione ─────────────────────────────────────────────

    def classify(self, text: str, feed_category: str = "") -> ClassificationResult:
        """Classifica un singolo articolo."""
        text_lower = text.lower()

        for dim, keywords in KEYWORD_OVERRIDES.items():
            for kw in keywords:
                pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                if re.search(pattern, text_lower):
                    return ClassificationResult(
                        dimension=dim, confidence=0.95, method="keyword"
                    )

        if self._load():
            result = self._classify_semantic(text)
            self._unload()
            return result

        return self._classify_fallback(text_lower, feed_category)

    def classify_batch(self, texts: list[str], feed_categories: list[str] | None = None) -> list[ClassificationResult]:
        """Classifica un batch di articoli."""
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
                        results[i] = ClassificationResult(
                            dimension=dim, confidence=0.95, method="keyword"
                        )
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                semantic_indices.append(i)
                semantic_texts.append(text)

        if semantic_texts and self._load():
            semantic_results = self._classify_semantic_batch(semantic_texts)
            self._unload()
            for idx, result in zip(semantic_indices, semantic_results):
                results[idx] = result
        else:
            for idx in semantic_indices:
                if results[idx] is None:
                    results[idx] = self._classify_fallback(
                        texts[idx].lower(), feed_categories[idx]
                    )

        return results

    def _classify_semantic(self, text: str) -> ClassificationResult:
        assert self._dim_embeddings is not None
        text_emb = self._encode([text])[0]

        best_dim = "non_pertinente"
        best_score = -1.0
        scores: dict[str, float] = {}

        for dim, dim_emb in self._dim_embeddings.items():
            score = float(np.dot(text_emb, dim_emb))
            scores[dim] = score
            if dim != "non_pertinente" and score > best_score:
                best_score = score
                best_dim = dim

        non_pert_score = scores.get("non_pertinente", 0.0)
        if best_score < RELEVANCE_THRESHOLD or non_pert_score > best_score:
            return ClassificationResult(
                dimension="non_pertinente",
                confidence=round(max(non_pert_score, 1.0 - best_score), 3),
                method="semantic",
            )

        return ClassificationResult(
            dimension=best_dim,
            confidence=round(best_score, 3),
            method="semantic",
        )

    def _classify_semantic_batch(self, texts: list[str]) -> list[ClassificationResult]:
        assert self._dim_embeddings is not None

        text_embs = self._encode(texts)
        dim_names = list(self._dim_embeddings.keys())
        dim_matrix = np.array([self._dim_embeddings[d] for d in dim_names])
        sim_matrix = text_embs @ dim_matrix.T

        results: list[ClassificationResult] = []
        non_pert_idx = dim_names.index("non_pertinente") if "non_pertinente" in dim_names else -1

        for i in range(len(texts)):
            scores = sim_matrix[i]
            best_score = -1.0
            best_dim = "non_pertinente"
            for j, dim in enumerate(dim_names):
                if dim != "non_pertinente" and scores[j] > best_score:
                    best_score = float(scores[j])
                    best_dim = dim

            non_pert_score = float(scores[non_pert_idx]) if non_pert_idx >= 0 else 0.0

            if best_score < RELEVANCE_THRESHOLD or non_pert_score > best_score:
                results.append(ClassificationResult(
                    dimension="non_pertinente",
                    confidence=round(max(non_pert_score, 1.0 - best_score), 3),
                    method="semantic",
                ))
            else:
                results.append(ClassificationResult(
                    dimension=best_dim,
                    confidence=round(best_score, 3),
                    method="semantic",
                ))

        return results

    @staticmethod
    def _classify_fallback(text_lower: str, feed_category: str) -> ClassificationResult:
        """Fallback keyword legacy se il modello non è disponibile."""
        from sentinella.collectors.mega_rss import DIMENSION_KEYWORDS, CATEGORY_DIMENSION

        for dim, keywords in DIMENSION_KEYWORDS.items():
            for kw in keywords:
                pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                if re.search(pattern, text_lower):
                    return ClassificationResult(
                        dimension=dim, confidence=0.5, method="fallback"
                    )
        dim = CATEGORY_DIMENSION.get(feed_category, "sociale")
        return ClassificationResult(dimension=dim, confidence=0.3, method="fallback")
