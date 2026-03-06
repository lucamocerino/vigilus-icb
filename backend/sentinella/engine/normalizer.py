from __future__ import annotations
"""
Normalizzazione z-score dei proxy rispetto alla baseline rolling 90gg.
Output: valore 0-100.
"""


def z_score(value: float, mean: float, std: float) -> float:
    """Z-score di un valore rispetto a media e deviazione standard."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def z_to_score(z: float, clip: float = 3.0) -> float:
    """
    Converte z-score in scala 0-100.
    z=0 → 30 (normale), z=+clip → 100 (critico), z<-clip → 0 (calmo).
    """
    # Clip z tra -clip e +clip
    z_clipped = max(-clip, min(clip, z))
    # Mappa [-clip, +clip] → [0, 100]
    # z=0 → 30 (leggermente sotto il centro per privilegiare "normale")
    score = ((z_clipped + clip) / (2 * clip)) * 100
    return round(max(0.0, min(100.0, score)), 2)


def normalize_proxy(
    value: float,
    mean: float,
    std: float,
    invert: bool = False,
) -> float:
    """
    Normalizza un singolo proxy su scala 0-100.
    invert=True: valori alti sono positivi (es. Goldstein scale positiva = pace).
    """
    z = z_score(value, mean, std)
    if invert:
        z = -z
    return z_to_score(z)


def aggregate_proxies(
    proxies: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """
    Media pesata di più proxy normalizzati → sotto-indice 0-100.
    Se weights è None, usa media semplice.
    """
    if not proxies:
        return 30.0  # Default "normale"

    if weights is None:
        return sum(proxies.values()) / len(proxies)

    total_weight = 0.0
    weighted_sum = 0.0
    for key, value in proxies.items():
        w = weights.get(key, 1.0)
        weighted_sum += value * w
        total_weight += w

    if total_weight == 0:
        return 30.0

    return round(weighted_sum / total_weight, 2)
