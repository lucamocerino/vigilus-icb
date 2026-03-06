# Sentinella Italia v2 — Piano Dettagliato

## Dashboard OSINT di Sicurezza Nazionale basata su Proxy

---

## 1. CONCEPT

### Problema
L'Italia non dispone di un indicatore pubblico di minaccia terroristica o di sicurezza (a differenza di UK, Canada, Francia). I dati esistenti sono dispersi in PDF, comunicati stampa e database internazionali non collegati tra loro. Il cittadino comune non ha strumenti per comprendere il livello di tensione del contesto in cui vive.

### Soluzione
Un **indice composito data-driven** costruito aggregando **proxy pubblici** — segnali indiretti ma misurabili che correlano con situazioni di tensione e rischio per la sicurezza nazionale. L'indice viene presentato come:

1. **Score sintetico 0-100** → visione immediata
2. **Radar plot multi-dimensione** → dettaglio per asse tematico

### Cosa NON è
- NON è un livello di allerta ufficiale del governo
- NON sostituisce le istituzioni di intelligence
- NON usa dati classificati
- NON vuole creare allarmismo

### Cosa È
- Un aggregatore OSINT trasparente e open source
- Un indicatore di **anomalia rispetto alla baseline storica**
- Uno strumento educativo per il cittadino
- Un progetto della community, verificabile e migliorabile

---

## 2. ARCHITETTURA DELLO SCORE

### 2.1 Le 6 Dimensioni del Radar

Lo score sintetico è la media pesata di 6 sotto-indici, ciascuno rappresentato come asse del radar plot:

```
                    GEOPOLITICA (25%)
                         ▲
                        / \
                       /   \
        CYBER (15%) ◄/     \► TERRORISMO (20%)
                     \     /
                      \   /
        SOCIALE (10%) ◄\ /► MILITARE (15%)
                        ▼
                   EVERSIONE (15%)
```

| # | Dimensione | Peso | Cosa misura | Proxy principali |
|---|-----------|------|-------------|------------------|
| 1 | **Geopolitica** | 25% | Tensione internazionale con impatto sull'Italia | GDELT Goldstein Scale, GDELT tone Italia, ACLED conflitti regioni limitrofe |
| 2 | **Terrorismo** | 20% | Rischio terroristico diretto e indiretto | GDELT eventi terrorismo EU, RSS keyword matching, Google Trends ("attentato", "allerta terrorismo") |
| 3 | **Cyber** | 15% | Attacchi informatici a infrastrutture italiane | Bollettini CSIRT Italia, Shodan anomalie porte IT, GreyNoise IP malevoli verso Italia |
| 4 | **Eversione** | 15% | Estremismo interno (anarco-insurrezionale, estrema destra/sinistra) | GDELT proteste Italia, ACLED Italia, RSS keyword matching |
| 5 | **Militare** | 15% | Movimenti militari anomali e postura difensiva | ADS-B voli militari da/per basi IT, NOTAM (Notice to Airmen) Italia, livelli allerta NATO (scraping) |
| 6 | **Sociale** | 10% | Tensione sociale, manifestazioni, disordini | Google Trends, GDELT proteste, sentiment social media |

### 2.2 Calcolo di ogni sotto-indice

Ogni dimensione produce un valore **0-100** calcolato come:

```
sotto_indice = normalize(
    valore_attuale - media_baseline_90gg
    ─────────────────────────────────────
         deviazione_standard_90gg
)
```

In pratica: **quanto il segnale attuale è anomalo rispetto agli ultimi 90 giorni**.

- **0-20** → Calmo (sotto la media)
- **21-40** → Normale (nella media)
- **41-60** → Attenzione (sopra la media)
- **61-80** → Elevato (1-2 deviazioni standard sopra)
- **81-100** → Critico (>2 deviazioni standard sopra)

### 2.3 Score sintetico

```python
score = (
    geopolitica * 0.25 +
    terrorismo  * 0.20 +
    cyber       * 0.15 +
    eversione   * 0.15 +
    militare    * 0.15 +
    sociale     * 0.10
)
```

Lo score viene mappato su una scala a 5 colori:

| Range | Livello | Colore | Significato |
|-------|---------|--------|-------------|
| 0-20 | CALMO | Verde | I proxy indicano una situazione sotto la media storica |
| 21-40 | NORMALE | Blu | I proxy sono nella norma storica |
| 41-60 | ATTENZIONE | Giallo | Alcuni proxy mostrano valori sopra la media |
| 61-80 | ELEVATO | Arancione | Anomalie significative su più dimensioni |
| 81-100 | CRITICO | Rosso | Anomalie estreme, situazione mai vista nei 90gg precedenti |

### 2.4 Frequenza di aggiornamento

**Ciclo bilanciato: ogni 4 ore** (6 aggiornamenti/giorno)

Orari: 02:00, 06:00, 10:00, 14:00, 18:00, 22:00 CET

Motivazione:
- GDELT aggiorna ogni 15 min → abbondantemente coperto
- Google Trends ha latenza ~24-48h → mediato dal ciclo di 4h
- ACLED è settimanale → integrato quando disponibile, ultimo valore mantenuto
- Evita il rumore dei dati sub-orari
- Sufficiente per catturare evoluzioni intra-giornaliere (es. attacco al mattino → score aggiornato a pranzo)

---

## 3. FONTI DATI — DETTAGLIO TECNICO

### 3.1 GDELT (Global Database of Events, Language and Tone)

**Ruolo**: Fonte primaria per geopolitica, terrorismo, eversione, sociale.

**Accesso**:
- API DOC 2.0: ricerca full-text su ultimi 3 mesi → `https://api.gdeltproject.org/api/v2/doc/doc`
- Google BigQuery: dataset completo dal 1979 → `gdelt-bq.gdeltv2.events`
- Download diretto: file giornalieri TSV → `http://data.gdeltproject.org/gdeltv2/lastupdate.txt`
- Libreria Python: `gdeltPyR` (pip install gdelt)

**Dati estratti per l'Italia**:

```
Per ogni ciclo di 4h:

GEOPOLITICA:
  - Media Goldstein Scale per eventi con Actor1=ITA o Actor2=ITA
  - Conteggio eventi con EventRootCode = 14 (PROTEST), 17 (COERCE), 18 (ASSAULT), 19 (FIGHT), 20 (MASS VIOLENCE)
  - Tone medio articoli che menzionano "Italy" + ("threat" OR "security" OR "terrorism" OR "attack")

TERRORISMO:
  - Conteggio eventi con EventCode = 1383 (threaten with mass violence), 180 (use unconventional mass violence)
  - Filtro per GeoCountry=IT o attori legati a IT
  - Volume articoli con tema TERROR + country IT

EVERSIONE:
  - Conteggio proteste (EventRootCode=14) in Italia
  - Conteggio riots (EventCode=145) in Italia
  - Tone medio copertura proteste italiane

SOCIALE:
  - Volume totale copertura mediatica Italia (indicatore di attenzione)
  - Rapporto articoli negativi/positivi su Italia
```

**Costo**: Gratuito (API e BigQuery con free tier)

### 3.2 ACLED (Armed Conflict Location & Event Data)

**Ruolo**: Fonte di verifica e calibrazione settimanale per eversione e geopolitica.

**Accesso**:
- API REST: `https://api.acleddata.com/acled/read`
- Richiede registrazione gratuita → API key + email
- Libreria R: `acled.api`; Python: richieste HTTP dirette

**Dati estratti**:

```
Settimanalmente:

EVERSIONE + SOCIALE:
  - Numero eventi "protests" e "riots" in Italia
  - Numero eventi "violence against civilians" in Italia
  - Numero eventi "strategic developments" in Italia

GEOPOLITICA:
  - Conflict Index Europa (indicatore regionale)
  - Eventi conflitto nelle regioni limitrofe (Mediterraneo, Balcani, Medio Oriente)
  - CAST forecast per Italia (previsione prossime 4 settimane)
```

**Costo**: Gratuito per uso non commerciale

### 3.3 Bollettini CSIRT Italia / ACN

**Ruolo**: Fonte primaria per dimensione Cyber.

**Accesso**:
- Pagina bollettini: `https://www.csirt.gov.it/contenuti/bollettini`
- Nessuna API ufficiale → scraping HTML + parsing
- Feed RSS potenzialmente disponibile

**Dati estratti**:

```
Ogni 4h (scraping):

CYBER:
  - Numero nuovi bollettini nelle ultime 24h
  - Gravità bollettini (parsing del testo: "critica", "alta", "media")
  - Conteggio CVE menzionate
  - Keyword: "infrastruttura critica", "PA", "energia", "trasporti"
```

**Costo**: Gratuito

### 3.4 Google Trends

**Ruolo**: Proxy di percezione pubblica e panico.

**Accesso**:
- Libreria Python: `pytrends` (non ufficiale ma stabile)
- Nessuna API ufficiale Google
- Rate limiting aggressivo → caching necessario

**Dati estratti**:

```
Ogni 4h (con caching 24h per le query lente):

TERRORISMO:
  - Interesse nel tempo per: "attentato", "terrorismo Italia", "allerta terrorismo"

SOCIALE:
  - Interesse per: "manifestazione Roma", "protesta", "sciopero"
  - Interesse per: "guerra", "bunker", "emergenza"

MILITARE:
  - Interesse per: "Aviano", "Sigonella", "basi NATO Italia"
```

**Costo**: Gratuito (con limiti di rate)

### 3.5 RSS / News Feed

**Ruolo**: Sentiment analysis in tempo reale su notizie italiane.

**Accesso**:
- ANSA RSS: `https://www.ansa.it/sito/ansait_rss.xml`
- AdnKronos RSS (sezione esteri e cronaca)
- Open RSS (aggregatore)

**Dati estratti**:

```
Ogni 4h:

TUTTI GLI ASSI:
  - Classificazione NLP di ogni articolo per dimensione (terrorismo, cyber, eversione, geopolitica, sociale, militare)
  - Sentiment score per articolo (spaCy + modello italiano)
  - Conteggio articoli per dimensione nelle ultime 24h
  - Spike detection: se il volume su un tema supera 2x la media settimanale
```

**Costo**: Gratuito

### 3.6 ADS-B / Dati Volo

**Ruolo**: Proxy per attività militare anomala.

**Accesso**:
- ADS-B Exchange API: `https://adsbexchange.com/data/` (a pagamento per uso intensivo)
- OpenSky Network: `https://opensky-network.org/` (gratuito per ricerca)
- NOTAM Italia: `https://notaminfo.com/` o ENAV

**Dati estratti**:

```
Ogni 4h:

MILITARE:
  - Numero voli militari da/per Aviano, Sigonella, Ghedi, Amendola
  - Anomalie: voli con transponder spento (perdita tracciamento)
  - NOTAM attivi per restrizioni spazio aereo Italia (indicatore di operazioni)
  - Confronto con baseline settimanale
```

**Costo**: OpenSky gratuito per ricerca; ADS-B Exchange ~$10/mese

---

## 4. ARCHITETTURA TECNICA

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                  │
│                                                              │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────┐  │
│  │  Score    │ │  Radar Plot  │ │ Timeline │ │  Dettaglio │  │
│  │  0-100   │ │  6 dimensioni│ │ storica  │ │  per asse  │  │
│  │  + colore│ │  (Recharts)  │ │ (D3.js)  │ │  + fonti   │  │
│  └──────────┘ └──────────────┘ └──────────┘ └───────────┘  │
│                                                              │
│  ┌──────────────────────┐ ┌───────────────────────────────┐ │
│  │  Mappa Italia        │ │  Feed notizie classificate    │ │
│  │  (Leaflet + GeoJSON) │ │  per dimensione               │ │
│  └──────────────────────┘ └───────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                     API (FastAPI)                             │
│                                                              │
│  GET /api/score/current      → score attuale + radar         │
│  GET /api/score/history      → storico score (30/90/365gg)   │
│  GET /api/dimension/{name}   → dettaglio singola dimensione  │
│  GET /api/events/latest      → ultimi eventi per dimensione  │
│  GET /api/sources/status     → stato fonti dati              │
│  GET /api/methodology        → spiegazione calcolo           │
│  WS  /ws/score               → websocket per aggiornamenti   │
├──────────────────────────────────────────────────────────────┤
│                   SCORE ENGINE (Python)                       │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 ScoreCalculator                      │    │
│  │                                                      │    │
│  │  1. Raccoglie dati grezzi da ogni collector          │    │
│  │  2. Normalizza ogni proxy (z-score vs baseline 90gg) │    │
│  │  3. Aggrega proxy → sotto-indice per dimensione      │    │
│  │  4. Media pesata → score sintetico                   │    │
│  │  5. Salva snapshot + emette evento websocket         │    │
│  │                                                      │    │
│  │  Esecuzione: ogni 4h via APScheduler                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │  GDELT   │ │  ACLED   │ │  CSIRT   │ │  Google      │   │
│  │ Collector│ │ Collector│ │ Scraper  │ │  Trends      │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│  ┌──────────┐ ┌──────────┐                                  │
│  │  RSS/NLP │ │  ADS-B   │                                  │
│  │ Analyzer │ │ Collector│                                  │
│  └──────────┘ └──────────┘                                  │
├──────────────────────────────────────────────────────────────┤
│                   DATA LAYER                                 │
│                                                              │
│  PostgreSQL                    Redis                         │
│  ├── scores (storico)          ├── cache API risposte        │
│  ├── raw_events (dati grezzi)  ├── cache Google Trends       │
│  ├── baselines (medie 90gg)    ├── ultimo score calcolato    │
│  ├── news_classified           └── lock job scheduler        │
│  └── source_status                                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. STRUTTURA REPOSITORY

```
sentinella-italia/
├── README.md                        # Overview + screenshot + quick start
├── LICENSE                          # AGPL-3.0 (copyleft per progetto civico)
├── CONTRIBUTING.md                  # Come contribuire
├── CODE_OF_CONDUCT.md              # Codice di condotta
├── METHODOLOGY.md                  # Spiegazione completa del calcolo score
├── docker-compose.yml              # Dev environment completo
├── .env.example                    # Template variabili d'ambiente
│
├── backend/
│   ├── pyproject.toml              # Dependencies (FastAPI, sqlalchemy, gdelt, spacy...)
│   ├── Dockerfile
│   ├── sentinella/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app + startup
│   │   ├── config.py               # Settings (pesi, soglie, intervalli)
│   │   │
│   │   ├── collectors/             # Un modulo per fonte dati
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Classe base BaseCollector
│   │   │   ├── gdelt.py            # GDELT events + tone + GKG
│   │   │   ├── acled.py            # ACLED API
│   │   │   ├── csirt.py            # Scraper bollettini CSIRT
│   │   │   ├── google_trends.py    # pytrends wrapper
│   │   │   ├── news_rss.py         # RSS parser + NLP classifier
│   │   │   └── adsb.py             # OpenSky / ADS-B Exchange
│   │   │
│   │   ├── engine/                 # Motore di calcolo score
│   │   │   ├── __init__.py
│   │   │   ├── normalizer.py       # Z-score normalization vs baseline
│   │   │   ├── dimensions.py       # Calcolo 6 sotto-indici
│   │   │   ├── score.py            # Aggregazione → score finale
│   │   │   └── baseline.py         # Gestione baseline rolling 90gg
│   │   │
│   │   ├── api/                    # Endpoint FastAPI
│   │   │   ├── __init__.py
│   │   │   ├── score.py            # /api/score/*
│   │   │   ├── dimensions.py       # /api/dimension/*
│   │   │   ├── events.py           # /api/events/*
│   │   │   ├── sources.py          # /api/sources/*
│   │   │   └── websocket.py        # WS /ws/score
│   │   │
│   │   ├── nlp/                    # NLP per classificazione notizie
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py       # Classificatore per dimensione
│   │   │   └── sentiment.py        # Analisi sentiment italiano
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── score.py            # ScoreSnapshot, DimensionScore
│   │   │   ├── event.py            # RawEvent, ClassifiedEvent
│   │   │   └── source.py           # SourceStatus
│   │   │
│   │   ├── scheduler.py            # APScheduler — ciclo 4h
│   │   └── db.py                   # Database connection
│   │
│   └── tests/
│       ├── test_collectors/
│       ├── test_engine/
│       ├── test_api/
│       └── fixtures/               # Dati di test realistici
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   │
│   │   ├── components/
│   │   │   ├── ScoreGauge.jsx      # Score 0-100 con colore
│   │   │   ├── RadarPlot.jsx       # Radar 6 dimensioni (Recharts)
│   │   │   ├── Timeline.jsx        # Storico score nel tempo
│   │   │   ├── DimensionCard.jsx   # Card dettaglio singola dimensione
│   │   │   ├── EventFeed.jsx       # Feed eventi classificati
│   │   │   ├── MappaItalia.jsx     # Mappa con indicatori regionali
│   │   │   ├── SourceStatus.jsx    # Stato salute fonti dati
│   │   │   ├── Methodology.jsx     # Pagina "come funziona"
│   │   │   └── Header.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useScore.js         # Hook per score corrente
│   │   │   ├── useWebSocket.js     # WS per aggiornamenti live
│   │   │   └── useDimension.js     # Hook per dettaglio dimensione
│   │   │
│   │   ├── utils/
│   │   │   ├── colors.js           # Palette score → colore
│   │   │   └── format.js           # Formattazione date, numeri
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   └── public/
│       ├── geojson/                # Confini Italia regioni/province
│       └── favicon.svg
│
├── data/
│   ├── geojson/
│   │   ├── italia-regioni.geojson
│   │   └── italia-province.geojson
│   ├── seed/
│   │   ├── baseline_initial.json   # Baseline iniziale per primo avvio
│   │   └── weights_default.json    # Pesi default dimensioni
│   └── samples/
│       ├── gdelt_sample.csv        # Dati esempio per sviluppo
│       └── acled_sample.json
│
├── docs/
│   ├── architettura.md
│   ├── fonti-dati.md               # Dettaglio ogni fonte
│   ├── calcolo-score.md            # Formula matematica completa
│   ├── api-reference.md            # Documentazione API
│   ├── guida-contribuire.md
│   └── etica.md                    # Considerazioni etiche
│
└── infra/
    ├── docker-compose.prod.yml
    ├── nginx.conf
    └── github-actions/
        ├── ci.yml                  # Test + lint
        └── deploy.yml              # Deploy automatico
```

---

## 6. ROADMAP DI SVILUPPO

### Fase 0 — Setup (Giorno 1-3)
- [ ] Creare repository GitHub
- [ ] README con concept, screenshot mockup, disclaimer
- [ ] docker-compose con PostgreSQL + Redis + FastAPI + Vite
- [ ] METHODOLOGY.md completo
- [ ] Modelli database (SQLAlchemy)
- [ ] Struttura cartelle completa

### Fase 1 — Collector GDELT (Settimana 1)
- [ ] `collectors/gdelt.py` — query BigQuery o API per eventi Italia
- [ ] Estrazione Goldstein Scale, tone, conteggio eventi per categoria
- [ ] Test con dati reali ultimi 7 giorni
- [ ] Salvataggio raw events su PostgreSQL
- [ ] **Deliverable**: primo sotto-indice "Geopolitica" calcolato da dati reali

### Fase 2 — Score Engine (Settimana 2)
- [ ] `engine/normalizer.py` — z-score normalization
- [ ] `engine/baseline.py` — calcolo media mobile 90gg
- [ ] `engine/dimensions.py` — aggregazione proxy → sotto-indice
- [ ] `engine/score.py` — media pesata → score 0-100
- [ ] `scheduler.py` — job ogni 4h
- [ ] Seed con baseline iniziale da dati GDELT storici
- [ ] **Deliverable**: score calcolato e salvato ogni 4h (anche se solo da GDELT)

### Fase 3 — API + Frontend MVP (Settimana 3)
- [ ] API endpoints: /score/current, /score/history, /dimension/{name}
- [ ] Frontend: ScoreGauge (numero + colore)
- [ ] Frontend: RadarPlot 6 assi (Recharts)
- [ ] Frontend: Timeline storica ultimi 30gg
- [ ] WebSocket per push aggiornamenti
- [ ] **Deliverable**: dashboard funzionante con score reale da GDELT

### Fase 4 — Collector aggiuntivi (Settimana 4-5)
- [ ] `collectors/news_rss.py` + `nlp/classifier.py` (spaCy italiano)
- [ ] `collectors/google_trends.py` (pytrends)
- [ ] `collectors/csirt.py` (scraper bollettini ACN)
- [ ] `collectors/acled.py` (API ACLED, ciclo settimanale)
- [ ] Integrazione tutti i collector nello Score Engine
- [ ] **Deliverable**: score composito da 5 fonti diverse

### Fase 5 — Collector militare + rifinitura (Settimana 6-7)
- [ ] `collectors/adsb.py` (OpenSky Network API)
- [ ] Parsing NOTAM Italia
- [ ] Frontend: DimensionCard per drill-down su ogni asse
- [ ] Frontend: EventFeed con notizie classificate
- [ ] Frontend: pagina Methodology interattiva
- [ ] Frontend: SourceStatus (salute delle fonti)
- [ ] **Deliverable**: tutte e 6 le dimensioni attive

### Fase 6 — Community e Deploy (Settimana 8-10)
- [ ] CI/CD con GitHub Actions
- [ ] Test suite completa (>80% coverage)
- [ ] Deploy su fly.io o Railway (backend) + Vercel (frontend)
- [ ] Documentazione API (Swagger/OpenAPI)
- [ ] CONTRIBUTING.md dettagliato
- [ ] Issue templates per bug e feature request
- [ ] Prima release pubblica v0.1.0
- [ ] Post su community (Spaghetti Open Data, onData, Reddit r/osint)

### Fase 7 — Evoluzione (Post-lancio)
- [ ] Notifiche push/email/Telegram per variazioni significative
- [ ] API pubblica per integrazioni terze
- [ ] Mappa Italia regionale con score per area
- [ ] Confronto con altri paesi EU (radar comparativo)
- [ ] Machine Learning per previsione a 24-48h
- [ ] App mobile (React Native)

---

## 7. DIPENDENZE TECNICHE

### Backend (Python 3.12+)

```toml
[project]
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy>=2.0",
    "asyncpg>=0.29",            # PostgreSQL async
    "redis>=5.0",
    "apscheduler>=3.10",
    "httpx>=0.27",              # HTTP client async
    "gdelt>=0.1",               # gdeltPyR
    "pytrends>=4.9",            # Google Trends
    "spacy>=3.7",               # NLP italiano
    "feedparser>=6.0",          # RSS parsing
    "beautifulsoup4>=4.12",     # HTML scraping
    "pydantic>=2.6",
    "numpy>=1.26",
    "pandas>=2.2",
    "websockets>=12.0",
]
```

Modello spaCy: `python -m spacy download it_core_news_lg`

### Frontend (Node 20+)

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "recharts": "^2.12",
    "leaflet": "^1.9",
    "react-leaflet": "^4.2",
    "d3": "^7.9",
    "lucide-react": "^0.360"
  },
  "devDependencies": {
    "vite": "^5.2",
    "@vitejs/plugin-react": "^4.2",
    "tailwindcss": "^3.4"
  }
}
```

### Infrastruttura

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: sentinella
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build: ./backend
    depends_on: [db, redis]
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD}@db/sentinella
      REDIS_URL: redis://redis:6379
      ACLED_API_KEY: ${ACLED_API_KEY}
      ACLED_EMAIL: ${ACLED_EMAIL}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
```

---

## 8. CONSIDERAZIONI ETICHE E LEGALI

### Disclaimer obbligatorio (sempre visibile nella UI)

> **Sentinella Italia** è un progetto open source indipendente che aggrega dati pubblici per fornire un indicatore sperimentale di contesto.
> NON è un livello di allerta ufficiale. NON sostituisce le istituzioni di sicurezza.
> Lo score riflette anomalie statistiche nei dati pubblici, non una valutazione di intelligence.
> In caso di emergenza reale, seguire le indicazioni delle autorità competenti.

### Principi di design etico

1. **Trasparenza totale**: ogni dato, peso e formula è visibile e documentato
2. **Nessun allarmismo**: il linguaggio è neutro ("anomalia statistica", non "pericolo")
3. **Attribuzione**: ogni proxy cita la fonte originale
4. **Nessun dato personale**: zero tracking utenti, zero analytics invasive
5. **Apertura a critiche**: issue tracker aperto, METHODOLOGY.md modificabile dalla community
6. **Responsabilità**: il progetto non incentiva comportamenti di panico

### Aspetti legali

- Tutte le fonti sono pubbliche e con licenze aperte (CC-BY, IODL, open API)
- Lo scraping è limitato a fonti che lo permettono o non lo vietano esplicitamente
- Rispetto dei rate limit di tutte le API
- Nessun dato classificato o protetto
- AGPL-3.0 per garantire che fork e derivati restino aperti

---

## 9. METRICHE DI SUCCESSO

| Metrica | Target v0.1 | Target v1.0 |
|---------|-------------|-------------|
| Fonti dati attive | ≥3 (GDELT, RSS, Google Trends) | 6/6 |
| Uptime score | 95% | 99% |
| Latenza aggiornamento | <5min dal ciclo | <2min |
| Copertura test | >60% | >80% |
| Contributor GitHub | 1 (tu) | ≥5 |
| Star GitHub | — | ≥100 |
| Correlazione con eventi reali | Qualitativa | Misurata retroattivamente |

---

## 10. RISCHI E MITIGAZIONI

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| API GDELT down/cambia | Media | Alto | Fallback su download diretto TSV; cache ultima risposta |
| Google Trends rate limiting | Alta | Medio | Cache 24h; rotazione IP; query batch notturne |
| Falsi positivi (score alto senza rischio reale) | Alta | Alto | Baseline lunga (90gg); comunicazione chiara; disclaimer |
| Percezione come "allarmismo" | Media | Alto | Linguaggio neutro; pagina metodologia; review community |
| ACLED chiude accesso gratuito | Bassa | Medio | Peso ACLED ridistribuito su GDELT |
| Scraping CSIRT bloccato | Bassa | Basso | RSS backup; contribuzione manuale community |

---

*Piano aggiornato il 5 marzo 2026 — Sentinella Italia v2*
*Approccio: OSINT proxy-based, radar multi-dimensione, ciclo 4h*
