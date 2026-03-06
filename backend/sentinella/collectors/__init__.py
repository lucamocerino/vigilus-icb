from sentinella.collectors.gdelt import GdeltCollector
from sentinella.collectors.news_rss import NewsRssCollector
from sentinella.collectors.csirt import CsirtCollector
from sentinella.collectors.google_trends import GoogleTrendsCollector
from sentinella.collectors.acled import AcledCollector
from sentinella.collectors.adsb import AdsbCollector
from sentinella.collectors.mega_rss import MegaRssCollector

ALL_COLLECTORS = [
    GdeltCollector,
    NewsRssCollector,
    CsirtCollector,
    GoogleTrendsCollector,
    AcledCollector,
    AdsbCollector,
    MegaRssCollector,
]

__all__ = [
    "GdeltCollector",
    "NewsRssCollector",
    "CsirtCollector",
    "GoogleTrendsCollector",
    "AcledCollector",
    "AdsbCollector",
    "MegaRssCollector",
    "ALL_COLLECTORS",
]
