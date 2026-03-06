"""
Trending Keywords — spike detection su parole chiave dai titoli RSS.
Rolling window 2h vs baseline 7gg, z-score per rilevare anomalie.
"""
from __future__ import annotations
import re
import time
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Stop words italiane da escludere
STOP_WORDS = frozenset({
    "il", "lo", "la", "le", "li", "gli", "un", "uno", "una", "dei", "del", "della",
    "delle", "dello", "degli", "di", "da", "in", "con", "su", "per", "tra", "fra",
    "che", "chi", "cui", "non", "più", "come", "anche", "sono", "stato", "essere",
    "hanno", "fatto", "dopo", "prima", "nel", "nella", "nelle", "nei", "suo", "sua",
    "suoi", "questo", "questa", "questi", "queste", "quello", "quella", "quelli",
    "quelle", "cosa", "dove", "quando", "perché", "come", "molto", "tutto", "tutti",
    "ogni", "alle", "alla", "allo", "agli", "era", "era", "sarà", "può", "già",
    "ancora", "sempre", "mai", "proprio", "solo", "altro", "altra", "altri", "altre",
    "news", "the", "and", "for", "with", "from", "has", "was", "are", "but", "not",
    "all", "new", "will", "been", "have", "his", "her", "its", "that", "this",
    "foto", "video", "aggiornamento", "breaking", "ultime", "notizie", "ore",
})

# Keyword importanti per la sicurezza (boost z-score)
SECURITY_KEYWORDS = frozenset({
    "attacco", "attentato", "bomba", "esplosione", "terrorismo", "isis",
    "hacker", "ransomware", "cyber", "malware", "breach",
    "guerra", "conflitto", "missili", "nucleare", "nato",
    "emergenza", "evacuazione", "allerta", "crisi", "terremoto",
    "protesta", "sciopero", "rivolta", "scontri", "manifestazione",
    "arresto", "mafia", "ndrangheta", "camorra", "sequestro",
    "militare", "esercito", "marina", "caccia", "drone",
})

# Pattern per estrarre parole significative
WORD_RE = re.compile(r'\b[a-zà-ü]{3,}\b', re.IGNORECASE)

# Stato baseline (aggiornato ad ogni ciclo)
_baseline_counts: dict[str, list[tuple[float, Counter]]] = {}  # {window_ts: Counter}
_baseline_window = 7 * 24 * 3600  # 7 giorni
_current_window: Counter = Counter()
_current_window_start: float = 0


def extract_keywords(text: str) -> list[str]:
    """Estrae parole significative da un testo."""
    words = WORD_RE.findall(text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) >= 3]


def update_trending(headlines: list[dict]) -> list[dict]:
    """
    Analizza le headline e calcola trending keywords con z-score.
    Ritorna lista ordinata per z-score decrescente.
    """
    global _current_window, _current_window_start

    now = time.time()
    window_2h = 2 * 3600

    # Reset finestra se scaduta
    if now - _current_window_start > window_2h:
        # Salva finestra precedente nella baseline
        if _current_window:
            _save_to_baseline(_current_window_start, _current_window)
        _current_window = Counter()
        _current_window_start = now

    # Conta keywords nella finestra corrente
    for h in headlines:
        title = h.get("title", "")
        keywords = extract_keywords(title)
        _current_window.update(keywords)

    # Calcola baseline stats
    baseline_stats = _compute_baseline_stats()

    # Calcola z-score per ogni keyword nella finestra corrente
    trending: list[dict] = []
    for word, count in _current_window.most_common(200):
        if count < 2:
            continue

        stats = baseline_stats.get(word, {"mean": 1.0, "std": 1.0})
        mean = stats["mean"] or 1.0
        std = stats["std"] or 1.0

        z = (count - mean) / std

        # Boost per security keywords
        is_security = word in SECURITY_KEYWORDS
        if is_security:
            z *= 1.5

        if z >= 1.0 or count >= 5 or is_security:
            # Trova dimensione più comune per questa keyword
            dimension = _guess_dimension(word)
            trending.append({
                "keyword": word,
                "count": count,
                "z_score": round(z, 2),
                "is_security": is_security,
                "dimension": dimension,
                "direction": "spike" if z >= 2.0 else "rising" if z >= 1.0 else "active",
            })

    trending.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return trending[:30]


def _save_to_baseline(timestamp: float, counter: Counter) -> None:
    """Salva una finestra nella baseline rolling."""
    global _baseline_counts
    now = time.time()

    # Aggiungi
    if "windows" not in _baseline_counts:
        _baseline_counts["windows"] = []
    _baseline_counts["windows"].append((timestamp, counter))

    # Pulizia vecchie finestre (> 7 giorni)
    _baseline_counts["windows"] = [
        (ts, c) for ts, c in _baseline_counts["windows"]
        if now - ts < _baseline_window
    ]


def _compute_baseline_stats() -> dict[str, dict[str, float]]:
    """Calcola media e std per ogni keyword dalla baseline."""
    windows = _baseline_counts.get("windows", [])
    if not windows:
        return {}

    all_words: set[str] = set()
    for _, counter in windows:
        all_words.update(counter.keys())

    stats: dict[str, dict[str, float]] = {}
    for word in all_words:
        values = [counter.get(word, 0) for _, counter in windows]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance) if variance > 0 else 1.0
        stats[word] = {"mean": mean, "std": std}

    return stats


DIMENSION_KEYWORD_MAP: dict[str, str] = {
    "terrorismo": "terrorismo", "attentato": "terrorismo", "isis": "terrorismo",
    "bomba": "terrorismo", "jihad": "terrorismo",
    "hacker": "cyber", "ransomware": "cyber", "malware": "cyber", "cyber": "cyber",
    "militare": "militare", "esercito": "militare", "nato": "militare",
    "marina": "militare", "drone": "militare", "missili": "militare",
    "guerra": "geopolitica", "conflitto": "geopolitica", "sanzioni": "geopolitica",
    "diplomazia": "geopolitica", "ucraina": "geopolitica", "russia": "geopolitica",
    "protesta": "sociale", "sciopero": "sociale", "manifestazione": "sociale",
    "rivolta": "eversione", "anarchico": "eversione", "estremismo": "eversione",
}


def _guess_dimension(word: str) -> str:
    return DIMENSION_KEYWORD_MAP.get(word, "geopolitica")
