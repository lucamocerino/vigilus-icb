"""
Seed baseline reale da 90 giorni di dati GDELT + CSIRT.

Uso:
    cd backend
    .venv/bin/python -m sentinella.scripts.seed_baseline

Durata: ~10 minuti (rispetta il rate limit GDELT di 1 req/7s).
Output: data/seed/baseline_real.json
"""
from __future__ import annotations
import json
import time
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
OUTPUT    = Path(__file__).parent.parent.parent.parent / "data" / "seed" / "baseline_real.json"

QUERIES = {
    "geopolitica": "Italy security",
    "terrorismo":  "Italy terror",
    "eversione":   "Italy protest",
    "sociale":     "Italy strike",
    "cyber":       "Italy cyber",
    "militare":    "Italy military",
}

import re
NEGATIVE_RE = re.compile(
    r'\b(attack|attacco|threat|minaccia|crisis|crisi|emergency|emergenza|'
    r'terror|bomb|explosion|allarme|warning|danger|riot|rivolta|violence|'
    r'violenza|hack|breach|ransomware|war|guerra)\b', re.IGNORECASE
)


def fetch_week(query: str, week_start: datetime, week_end: datetime) -> dict:
    """Fetch articoli per una settimana specifica."""
    params = {
        "query":         query,
        "mode":          "artlist",
        "maxrecords":    "250",
        "format":        "json",
        "startdatetime": week_start.strftime("%Y%m%d%H%M%S"),
        "enddatetime":   week_end.strftime("%Y%m%d%H%M%S"),
    }
    for attempt in range(3):
        try:
            r = httpx.get(GDELT_API, params=params, timeout=20)
            if r.status_code == 429:
                print(f"    429 — attendo {10 * (attempt+1)}s...")
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code != 200 or not r.text.strip():
                return {"article_count": 0, "negative_ratio": 0.0}
            arts = r.json().get("articles") or []
            neg = sum(1 for a in arts if NEGATIVE_RE.search(a.get("title", "")))
            return {
                "article_count":  len(arts),
                "negative_ratio": round(neg / len(arts), 3) if arts else 0.0,
            }
        except Exception as e:
            print(f"    Errore: {e}")
            time.sleep(5)
    return {"article_count": 0, "negative_ratio": 0.0}


def calc_stats(values: list[float]) -> dict[str, float]:
    if len(values) < 2:
        return {"mean": values[0] if values else 0.0, "std": 1.0}
    return {
        "mean": round(statistics.mean(values), 3),
        "std":  round(statistics.stdev(values) or 1.0, 3),
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    # 13 settimane = ~90 giorni
    weeks = [
        (now - timedelta(weeks=i+1), now - timedelta(weeks=i))
        for i in range(13)
    ]
    weeks.reverse()  # dal più vecchio al più recente

    print(f"Seed baseline da {len(weeks)} settimane di dati GDELT")
    print(f"Durata stimata: ~{len(QUERIES) * len(weeks) * 7 // 60} minuti\n")

    # Struttura: { dimensione: { proxy: [valori per settimana] } }
    collected: dict[str, dict[str, list]] = {
        dim: {"article_count": [], "negative_ratio": []}
        for dim in QUERIES
    }

    total = len(QUERIES) * len(weeks)
    done  = 0

    for dim, query in QUERIES.items():
        print(f"\n[{dim}]")
        for w_start, w_end in weeks:
            done += 1
            print(f"  [{done}/{total}] {w_start.strftime('%d/%m')}–{w_end.strftime('%d/%m')}...", end=" ", flush=True)
            data = fetch_week(query, w_start, w_end)
            # Skip weeks where 0 articles were returned — likely rate-limit artifacts
            # (broad queries like "Italy security" always have articles in a 7-day window)
            if data["article_count"] > 0:
                collected[dim]["article_count"].append(data["article_count"])
                collected[dim]["negative_ratio"].append(data["negative_ratio"])
            print(f"{data['article_count']} art, neg={data['negative_ratio']:.2f}")
            time.sleep(7)  # rate limit

    # Calcola statistiche
    baselines: dict[str, dict[str, dict]] = {}
    for dim, proxies in collected.items():
        baselines[dim] = {}
        for proxy, values in proxies.items():
            baselines[dim][proxy] = calc_stats([v for v in values if v is not None])
            print(f"  {dim}.{proxy}: mean={baselines[dim][proxy]['mean']}, std={baselines[dim][proxy]['std']}")

    OUTPUT.write_text(json.dumps(baselines, indent=2, ensure_ascii=False))
    print(f"\nBaseline salvata in: {OUTPUT}")
    print("Riavvia il backend per caricarla automaticamente.")


if __name__ == "__main__":
    main()
