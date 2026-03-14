# 🧓 Boomer Assistant

Assistente desktop per persone non tecniche. Usa AI locale (Ollama + Qwen2.5) con interfaccia vocale completamente offline.

## Stack

| Componente | Tecnologia |
|---|---|
| Desktop | Tauri v2 (Rust) |
| UI | React + TypeScript + Tailwind |
| AI Chat | Ollama + Qwen2.5:7B-Q4 (~2.8GB RAM) |
| Speech-to-Text | Whisper.cpp via whisper-rs (~500MB RAM) |
| Text-to-Speech | Piper TTS (~100MB RAM) |
| Vision (on-demand) | Qwen2.5-VL:3B-Q4 |
| i18n | Italiano 🇮🇹 / English 🇬🇧 |

## Prerequisiti

1. **Rust** — [rustup.rs](https://rustup.rs)
2. **Node.js** ≥ 18
3. **Ollama** — [ollama.com](https://ollama.com)
4. **Piper TTS** — [github.com/rhasspy/piper](https://github.com/rhasspy/piper)

## Setup

```bash
# 1. Installa dipendenze frontend
npm install

# 2. Scarica il modello Ollama
ollama pull qwen2.5:7b

# 3. Scarica il modello Whisper (small, ~500MB)
mkdir -p src-tauri/models
curl -L -o src-tauri/models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin

# 4. Scarica voce Piper italiana
curl -L -o src-tauri/models/it_IT-riccardo-x_low.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx
curl -L -o src-tauri/models/it_IT-riccardo-x_low.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx.json

# 5. Avvia in dev mode
npm run tauri dev
```

## Struttura Progetto

```
boomer-assistant/
├── src/                    # Frontend React
│   ├── components/         # VoiceButton, MessageLog, StatusBar
│   ├── hooks/              # useChat, useVoiceRecognition, useTextToSpeech
│   ├── i18n/               # Traduzioni IT/EN
│   ├── services/           # Ollama client, Tool system
│   └── types/              # TypeScript types
├── src-tauri/              # Backend Rust
│   ├── src/commands/       # Tauri commands (voice, audio, system)
│   └── models/             # Whisper + Piper models (gitignored)
└── README.md
```

## Tools Disponibili

| Tool | Descrizione |
|---|---|
| `get_audio_devices` | Lista dispositivi audio |
| `set_volume` | Imposta volume (0-100) |
| `fix_audio_issues` | Diagnostica e fix audio |
| `open_app` | Apri Facebook, Zoom, WhatsApp... |
| `get_system_info` | Info sistema operativo |

## Comandi

```bash
npm run tauri dev     # Sviluppo con hot reload
npm run tauri build   # Build produzione
npm run dev           # Solo frontend (senza Tauri)
```

## RAM Stimata

| Componente | RAM |
|---|---|
| Qwen2.5:7B-Q4 | ~2.8GB |
| Whisper small | ~500MB |
| Piper TTS | ~100MB |
| App Tauri | ~200MB |
| **Totale** | **~3.6GB** |

Funziona su PC con 8GB RAM ✅
