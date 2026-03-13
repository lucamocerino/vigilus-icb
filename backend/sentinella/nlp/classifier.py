"""Classificatore semantico per notizie italiane.

Usa sentence-transformers con modello multilingue per classificare
articoli nelle dimensioni di sicurezza tramite cosine similarity.
"""

from __future__ import annotations

import logging
import re
import threading
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

# Soglia minima di similarità: sotto questa → non_pertinente
RELEVANCE_THRESHOLD = 0.25

# Keyword override per casi ovvi (velocizza e risparmia risorse)
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
    """Classificatore semantico basato su sentence-transformers."""

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self) -> None:
        self._model = None
        self._dim_embeddings: dict[str, np.ndarray] | None = None
        self._ready = False

    # ── Lazy loading ────────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Carica il modello se non già fatto. Restituisce True se pronto."""
        if self._ready:
            return True
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("[classifier] Caricamento modello %s …", self.MODEL_NAME)
            self._model = SentenceTransformer(self.MODEL_NAME)

            # Pre-calcola embedding di riferimento per ogni dimensione
            self._dim_embeddings = {}
            for dim, descriptions in DIMENSION_DESCRIPTIONS.items():
                embs = self._model.encode(descriptions, normalize_embeddings=True)
                # Media degli embedding come rappresentazione della dimensione
                self._dim_embeddings[dim] = np.mean(embs, axis=0)
                # Normalizza il vettore medio
                norm = np.linalg.norm(self._dim_embeddings[dim])
                if norm > 0:
                    self._dim_embeddings[dim] /= norm

            self._ready = True
            logger.info("[classifier] Modello pronto — %d dimensioni caricate", len(DIMENSION_DESCRIPTIONS))
            return True
        except Exception as e:
            logger.warning("[classifier] Impossibile caricare il modello: %s", e)
            return False

    # ── Classificazione ─────────────────────────────────────────────

    def classify(self, text: str, feed_category: str = "") -> ClassificationResult:
        """Classifica un singolo articolo.

        1. Prova keyword override (veloce, alta precisione)
        2. Prova classificazione semantica
        3. Fallback su categoria feed
        """
        text_lower = text.lower()

        # Keyword override per casi ovvi
        for dim, keywords in KEYWORD_OVERRIDES.items():
            for kw in keywords:
                pattern = r'(?<![a-zA-Zà-ú])' + re.escape(kw) + r'(?![a-zA-Zà-ú])'
                if re.search(pattern, text_lower):
                    return ClassificationResult(
                        dimension=dim, confidence=0.95, method="keyword"
                    )

        # Classificazione semantica
        if self._ensure_loaded():
            return self._classify_semantic(text)

        # Fallback keyword legacy
        return self._classify_fallback(text_lower, feed_category)

    def classify_batch(self, texts: list[str], feed_categories: list[str] | None = None) -> list[ClassificationResult]:
        """Classifica un batch di articoli (più efficiente per molti articoli)."""
        if feed_categories is None:
            feed_categories = [""] * len(texts)

        results: list[ClassificationResult] = [None] * len(texts)  # type: ignore
        semantic_indices: list[int] = []
        semantic_texts: list[str] = []

        # Prima passa: keyword override
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

        # Seconda passa: semantica batch
        if semantic_texts and self._ensure_loaded():
            semantic_results = self._classify_semantic_batch(semantic_texts)
            for idx, result in zip(semantic_indices, semantic_results):
                results[idx] = result
        else:
            # Fallback per quelli non classificati
            for idx in semantic_indices:
                if results[idx] is None:
                    results[idx] = self._classify_fallback(
                        texts[idx].lower(), feed_categories[idx]
                    )

        return results

    def _classify_semantic(self, text: str) -> ClassificationResult:
        """Classificazione semantica di un singolo testo."""
        assert self._model is not None and self._dim_embeddings is not None

        text_emb = self._model.encode([text], normalize_embeddings=True)[0]

        best_dim = "non_pertinente"
        best_score = -1.0
        scores: dict[str, float] = {}

        for dim, dim_emb in self._dim_embeddings.items():
            score = float(np.dot(text_emb, dim_emb))
            scores[dim] = score
            if dim != "non_pertinente" and score > best_score:
                best_score = score
                best_dim = dim

        # Se il non_pertinente ha score più alto, o il best è sotto soglia
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
        """Classificazione semantica batch (un solo encode per tutti i testi)."""
        assert self._model is not None and self._dim_embeddings is not None

        text_embs = self._model.encode(texts, normalize_embeddings=True, batch_size=64)

        # Matrice dimensioni: (n_dims, emb_size)
        dim_names = list(self._dim_embeddings.keys())
        dim_matrix = np.array([self._dim_embeddings[d] for d in dim_names])

        # Cosine similarity: (n_texts, n_dims)
        sim_matrix = text_embs @ dim_matrix.T

        results: list[ClassificationResult] = []
        non_pert_idx = dim_names.index("non_pertinente") if "non_pertinente" in dim_names else -1

        for i in range(len(texts)):
            scores = sim_matrix[i]

            # Trova best dimensione (escluso non_pertinente)
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
