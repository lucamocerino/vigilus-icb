from fastapi import APIRouter
from sentinella.api import score, dimensions, events, sources, methodology, cache, map, narrative
from sentinella.api import export, compare, regional, headlines, trending, layers
from sentinella.api import correlations, convergence, digest, osint

api_router = APIRouter()
api_router.include_router(score.router)
api_router.include_router(dimensions.router)
api_router.include_router(events.router)
api_router.include_router(sources.router)
api_router.include_router(methodology.router)
api_router.include_router(cache.router)
api_router.include_router(map.router)
api_router.include_router(narrative.router)
api_router.include_router(export.router)
api_router.include_router(compare.router)
api_router.include_router(regional.router)
api_router.include_router(headlines.router)
api_router.include_router(trending.router)
api_router.include_router(layers.router)
api_router.include_router(correlations.router)
api_router.include_router(convergence.router)
api_router.include_router(digest.router)
api_router.include_router(osint.router)
