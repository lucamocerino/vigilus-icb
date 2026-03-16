"""Classificatore TF-IDF leggero per notizie italiane.

Gira interamente in-process usando solo numpy (~2MB).
Nessun subprocess, nessun modello ONNX, nessuna dipendenza extra.

Costruisce un vocabolario dalle DIMENSION_DESCRIPTIONS e classifica
i testi tramite cosine similarity su vettori TF-IDF.
"""

from __future__ import annotations

import math
import re
import logging
from collections import Counter
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Stopwords italiane essenziali
_STOP_IT = frozenset(
    "di da in con su per tra fra il lo la le li gli i un uno una che è e"
    " del dello della dei degli delle al allo alla ai agli alle nel nello"
    " nella nei negli nelle sul sullo sulla sui sugli sulle a o non si no"
    " ma come anche più molto questo quello essere avere fare suo loro ha"
    " sono stato era ci se io tu lui lei noi voi chi cosa dove quando".split()
)


def _tokenize(text: str) -> list[str]:
    """Tokenizzazione semplice: lowercase, split su non-alfanumerici, rimuovi stop."""
    tokens = re.findall(r"[a-zà-ú0-9\-]{2,}", text.lower())
    return [t for t in tokens if t not in _STOP_IT]


class TfidfLiteClassifier:
    """Classificatore TF-IDF in-process. Zero subprocess, ~2MB RAM."""

    def __init__(self, dim_descriptions: dict[str, list[str]]) -> None:
        self._dim_names: list[str] = list(dim_descriptions.keys())
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._dim_vectors: np.ndarray | None = None
        self._build_index(dim_descriptions)

    def _build_index(self, dim_descriptions: dict[str, list[str]]) -> None:
        """Costruisce vocabolario, IDF e vettori dimensione."""
        # Raccogli tutti i documenti (ogni descrizione è un documento)
        all_docs: list[list[str]] = []
        doc_dim_map: list[str] = []
        for dim, descs in dim_descriptions.items():
            for desc in descs:
                tokens = _tokenize(desc)
                all_docs.append(tokens)
                doc_dim_map.append(dim)

        # Costruisci vocabolario
        vocab_set: set[str] = set()
        for doc in all_docs:
            vocab_set.update(doc)
        self._vocab = {word: i for i, word in enumerate(sorted(vocab_set))}
        vocab_size = len(self._vocab)

        # Calcola IDF
        doc_freq = np.zeros(vocab_size, dtype=np.float32)
        n_docs = len(all_docs)
        for doc in all_docs:
            seen = set(doc)
            for word in seen:
                if word in self._vocab:
                    doc_freq[self._vocab[word]] += 1

        self._idf = np.log((n_docs + 1) / (doc_freq + 1)) + 1  # smooth IDF

        # Costruisci vettori TF-IDF per dimensione (media dei documenti)
        dim_vectors = np.zeros((len(self._dim_names), vocab_size), dtype=np.float32)
        dim_doc_counts: dict[str, int] = Counter()

        for doc, dim in zip(all_docs, doc_dim_map):
            dim_idx = self._dim_names.index(dim)
            tf_vec = self._text_to_tfidf(doc)
            dim_vectors[dim_idx] += tf_vec
            dim_doc_counts[dim] += 1

        # Media per dimensione
        for i, dim in enumerate(self._dim_names):
            count = dim_doc_counts.get(dim, 1)
            dim_vectors[i] /= count

        # Normalizza L2
        norms = np.linalg.norm(dim_vectors, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        self._dim_vectors = dim_vectors / norms

        logger.info(
            f"[tfidf] Index costruito: {vocab_size} termini, "
            f"{len(self._dim_names)} dimensioni, {n_docs} documenti"
        )

    def _text_to_tfidf(self, tokens: list[str]) -> np.ndarray:
        """Converte una lista di token in vettore TF-IDF."""
        vocab_size = len(self._vocab)
        tf = np.zeros(vocab_size, dtype=np.float32)
        counts = Counter(tokens)
        for word, count in counts.items():
            if word in self._vocab:
                tf[self._vocab[word]] = count
        # Normalizzazione TF logaritmica
        tf = np.where(tf > 0, 1 + np.log(np.maximum(tf, 1)), 0)
        return tf * self._idf

    def classify(self, text: str) -> tuple[str, float]:
        """Classifica un testo. Ritorna (dimensione, confidence)."""
        tokens = _tokenize(text)
        if not tokens:
            return "non_pertinente", 0.0

        vec = self._text_to_tfidf(tokens)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return "non_pertinente", 0.0
        vec = vec / norm

        similarities = self._dim_vectors @ vec

        # Trova la migliore dimensione pertinente (escludendo non_pertinente)
        non_pert_idx = (
            self._dim_names.index("non_pertinente")
            if "non_pertinente" in self._dim_names
            else -1
        )

        best_idx = -1
        best_score = -1.0
        for j, dim in enumerate(self._dim_names):
            if j != non_pert_idx and similarities[j] > best_score:
                best_score = float(similarities[j])
                best_idx = j

        non_pert_score = float(similarities[non_pert_idx]) if non_pert_idx >= 0 else 0.0

        # Se non_pertinente ha score più alto o il migliore è troppo debole
        if non_pert_score > best_score or best_score < 0.15:
            return "non_pertinente", round(max(non_pert_score, 0.3), 3)

        return self._dim_names[best_idx], round(min(best_score, 0.90), 3)

    def classify_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        """Classifica un batch di testi."""
        return [self.classify(text) for text in texts]
