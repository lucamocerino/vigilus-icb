<p align="center">
  <img src="frontend/public/favicon.svg" alt="VIGILUS Logo" width="200" />
</p>

<h1 align="center">VIGILUS — Italy Crisis Board</h1>

<p align="center">
  <em>Real-time OSINT intelligence dashboard for Italy's national security</em>
</p>

<p align="center">
  <a href="https://vigilus-frontend.onrender.com"><img src="https://img.shields.io/badge/🔴_LIVE_DEMO-vigilus.onrender.com-indigo?style=for-the-badge" alt="Live Demo" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL%20v3-blue.svg" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.12-green.svg" alt="Python" />
  <img src="https://img.shields.io/badge/React-18-61DAFB.svg" alt="React" />
  <img src="https://img.shields.io/badge/API-32%20endpoints-indigo.svg" alt="API" />
  <img src="https://img.shields.io/badge/Tests-176%20passed-brightgreen.svg" alt="Tests" />
  <img src="https://img.shields.io/badge/Coverage-69%25-yellow.svg" alt="Coverage" />
</p>

<p align="center">
  <img src="docs/screenshot.png" alt="VIGILUS Dashboard" width="900" />
</p>

---

[🇮🇹 Italiano](#italiano) · [🇬🇧 English](#english)

<a id="italiano"></a>

## 🇮🇹 Italiano

Dashboard OSINT open source per il monitoraggio della sicurezza nazionale italiana. Layout Bloomberg terminal con mappa operativa e pannelli intelligence. Basata esclusivamente su dati pubblici.

> **⚠️ NON è un livello di allerta ufficiale.** Aggrega anomalie statistiche su proxy pubblici.

### Stack

| Layer | Tecnologie |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, APScheduler, spaCy, sentence-transformers, Alembic |
| Frontend | React 18, Vite, Recharts, Leaflet, Tailwind CSS |
| Database | SQLite (dev) / PostgreSQL 16 (prod via Supabase/Render) |
| Infra | Render, Docker Compose, Caddy HTTPS, GitHub Actions CI/CD |
| Sicurezza | API key auth, rate limiting, CORS, security headers, Sentry |
| Intelligence | NLP classifier semantico (sentence-transformers), ML browser-side (threat + sentiment), Headline Memory RAG (IndexedDB) |
| Monitoring | Prometheus `/metrics`, structured JSON logging |

### Funzionalità

**Layout Bloomberg Terminal**
- Mappa operativa a sinistra (60%) con 6 data layer toggle e resize drag handle
- Pannelli intelligence a destra (40%) scrollabili
- News ticker scrollante da 50+ feed RSS italiani
- Score bar con indice composito + 6 dimensioni in tempo reale

**Score & Dimensioni**
- Indice composito 0–100 — media pesata di 6 dimensioni via z-score vs baseline 90gg
- Geopolitica (25%) · Terrorismo (20%) · Cyber (15%) · Eversione (15%) · Militare (15%) · Sociale (10%)
- 🟢 CALMO · 🔵 NORMALE · 🟡 ATTENZIONE · 🟠 ELEVATO · 🔴 CRITICO

**Mappa Operativa — 6 Layer**
- Eventi geo-taggati via NER spaCy
- 14 basi militari NATO/USA (Aviano, Sigonella, Ghedi, Camp Darby...)
- 18 infrastrutture critiche (porti, aeroporti, centrali, cavi sottomarini, TAP)
- Terremoti INGV ultimi 7gg (M2+)
- Voli militari ADS-B (OpenSky Network)
- Convergenza geografica multi-dimensione

**Intelligence Browser-Side**
- Headline Memory (RAG) — 5.000 headline in IndexedDB, ricerca semantica
- ML Classifier — threat detection + sentiment in Web Worker
- Keyword Monitor — alert personalizzabili con localStorage
- Trending keywords — spike detection z-score (2h rolling vs 7gg baseline)

**OSINT & Data — 8 Collector + 50+ RSS**
- ANSA, AGI, Adnkronos, Repubblica, Corriere, Sole24Ore, Difesa Online, Formiche, CSIRT, Red Hot Cyber, Reuters, BBC...
- GDELT, CSIRT Italia, Google Trends, ACLED, OpenSky ADS-B, INGV
- **Classificazione semantica NLP** — sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) con cosine similarity per dimensione, keyword fast-pass per terrorismo/cyber, filtro automatico notizie non pertinenti (gossip, sport, spettacolo), confidence score 0–1 per ogni articolo
- Hotspot escalation con trend 48h
- Cross-stream correlation (Pearson) + alert spike simultanei
- Dossier regionale (14 regioni italiane)
- Prediction markets (8 scenari geopolitici)
- Outage monitor (TIM, Vodafone, Enel, SPID...)
- Daily digest automatico 24h

**Strumenti**
- ⌘K Command palette — fuzzy search
- Dark/Light theme con glassmorphism
- IT/EN toggle lingua
- Confronto periodi (settimana/mese/trimestre)
- Export CSV/Report
- Condivisione Twitter, Telegram, WhatsApp
- TG Live (Sky TG24, Rai News 24, TGCOM24)
- Narrativa AI (Claude, opzionale)
- WebSocket real-time + URL state sharing
- PWA installabile + pannelli ridimensionabili

### Avvio rapido

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"
uvicorn sentinella.main:app --reload    # http://localhost:8000

# Frontend
cd frontend
npm install && npm run dev              # http://localhost:3000

# Docker (tutto insieme)
cp .env.example .env && docker compose up -d
```

### Test

```bash
cd backend
python -m pytest tests/ -v --cov=sentinella
# 176 test · 69% coverage · 0 lint errors
```

### Fonti dati

| Fonte | Dati | Cache |
|---|---|---|
| **Mega RSS** (50+ feed) | Agenzie, quotidiani, difesa, cyber, geopolitica — classificazione semantica NLP | 15min |
| GDELT Project | Articoli internazionali, negatività | 1h |
| CSIRT Italia | Bollettini cyber, CVE, infrastrutture | 30min |
| Google Trends | Termini chiave italiani | 24h |
| ACLED | Proteste e scontri Italia | 7gg |
| OpenSky Network | Voli militari su 5 basi ADS-B | 1h |
| INGV | Terremoti M2+ ultimi 7gg | 30min |

### API (32 endpoint)

<details>
<summary>Lista completa endpoint</summary>

```
GET  /api/score/current              score + dimensioni + confidence
GET  /api/score/history              storico (?days=30)
GET  /api/score/anomalies            proxy con |z| >= 1.5σ
GET  /api/score/compare              confronto periodi
GET  /api/score/correlations         correlazioni cross-stream
GET  /api/score/narrative            sintesi AI
POST /api/score/trigger              forza ricalcolo (solo debug)
GET  /api/dimension/{name}           dettaglio dimensione
GET  /api/dimension/{name}/history   storico dimensione
GET  /api/events/latest              eventi classificati
GET  /api/events/search              full-text search
GET  /api/headlines                  titoli ticker (50+ fonti)
GET  /api/trending                   keywords spike detection
GET  /api/hotspots                   escalation per dimensione
GET  /api/predictions                prediction markets
GET  /api/outages                    stato infrastrutture digitali
GET  /api/digest/daily               riepilogo 24h
GET  /api/earthquakes                terremoti INGV
GET  /api/flights                    voli militari ADS-B
GET  /api/region/{name}              dossier regionale
GET  /api/map/events                 eventi geo-taggati NER
GET  /api/map/regional               breakdown Nord/Centro/Sud
GET  /api/map/convergence            convergenza multi-dimensione
GET  /api/layers/military            GeoJSON 14 basi NATO
GET  /api/layers/infrastructure      GeoJSON 18 infrastrutture
GET  /api/layers/all                 tutti i data layer
GET  /api/export/csv                 download CSV
GET  /api/export/report              report JSON
GET  /api/sources/status             stato fonti
GET  /api/cache/status               cache collector
GET  /api/methodology                documentazione
GET  /health                         health check
GET  /metrics                        Prometheus metrics
WS   /ws/score                       WebSocket real-time
```
</details>

### Deploy

Il progetto è deployato su **Render** (backend + frontend) con **PostgreSQL** (Render DB free).

```bash
# Self-hosted con Docker
cp .env.production.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose exec backend alembic upgrade head
```

---

<a id="english"></a>

## 🇬🇧 English

Open source OSINT dashboard for monitoring Italy's national security. Bloomberg terminal-style layout with operational map and intelligence panels. Based exclusively on public data.

> **⚠️ NOT an official alert level.** Aggregates statistical anomalies from public proxies.

### Features

- **Composite score 0–100** across 6 security dimensions with z-score normalization
- **Operational map** with 6 toggleable data layers (NATO bases, infrastructure, earthquakes, flights, convergence)
- **50+ Italian RSS feeds** with NLP semantic classification and trending keyword spike detection
- **Smart news classifier** — sentence-transformers with cosine similarity, automatic filtering of irrelevant content, confidence scores
- **Browser-side ML** — threat classification + sentiment analysis in Web Worker
- **Headline Memory RAG** — 5,000 headlines indexed in IndexedDB for semantic search
- **Cross-stream correlation** — Pearson across dimensions, simultaneous spike alerts
- **Regional briefs** for 14 Italian regions
- **Live TV** — Sky TG24, Rai News 24, TGCOM24
- **⌘K Command palette**, dark/light theme, IT/EN, PWA, resizable panels
- **32 API endpoints**, 176 tests, 69% coverage

### Data Sources

8 collectors + 50+ RSS feeds: GDELT, CSIRT Italia, ACLED, Google Trends, OpenSky ADS-B, INGV earthquakes, ANSA, AGI, Adnkronos, Repubblica, Corriere, defense & cyber specialized feeds. News classified via NLP semantic embeddings with automatic irrelevant content filtering.

### Quick Start

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install ".[dev]"
uvicorn sentinella.main:app --reload

cd frontend && npm install && npm run dev
```

### Stack

FastAPI · React 18 · SQLAlchemy 2.0 · sentence-transformers · Leaflet · Tailwind CSS · PostgreSQL · Render · GitHub Actions

### License

AGPL-3.0
