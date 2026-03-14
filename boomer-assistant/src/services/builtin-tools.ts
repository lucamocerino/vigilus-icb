import { invoke } from "@tauri-apps/api/core";
import { registerTool } from "./tools";

registerTool({
  name: "get_audio_devices",
  description: "Elenca i dispositivi audio del computer (casse, cuffie, microfoni)",
  parameters: {},
  execute: async () => {
    try {
      const devices = await invoke<string>("get_audio_devices");
      return devices;
    } catch (err) {
      return `Errore nel recupero dispositivi audio: ${err}`;
    }
  },
});

registerTool({
  name: "set_volume",
  description: "Imposta il volume del computer a un livello specifico (0-100)",
  parameters: {
    level: {
      type: "number",
      description: "Livello del volume da 0 (muto) a 100 (massimo)",
      required: true,
    },
  },
  execute: async (params) => {
    try {
      const level = Number(params.level);
      await invoke("set_volume", { level });
      return `Volume impostato a ${level}%`;
    } catch (err) {
      return `Errore nell'impostazione del volume: ${err}`;
    }
  },
});

registerTool({
  name: "fix_audio_issues",
  description: "Diagnostica e prova a risolvere problemi audio comuni",
  parameters: {},
  execute: async () => {
    try {
      const result = await invoke<string>("fix_audio_issues");
      return result;
    } catch (err) {
      return `Errore nella diagnostica audio: ${err}`;
    }
  },
});

registerTool({
  name: "open_app",
  description:
    "Apre un'applicazione sul computer. Supporta: Facebook, WhatsApp, Zoom, YouTube, Email, Browser",
  parameters: {
    name: {
      type: "string",
      description: "Nome dell'applicazione da aprire",
      required: true,
      enum: ["facebook", "whatsapp", "zoom", "youtube", "email", "browser"],
    },
  },
  execute: async (params) => {
    try {
      const result = await invoke<string>("open_app", {
        appName: String(params.name).toLowerCase(),
      });
      return result;
    } catch (err) {
      return `Errore nell'apertura di ${params.name}: ${err}`;
    }
  },
});

registerTool({
  name: "get_system_info",
  description: "Mostra informazioni sul computer: sistema operativo, memoria, processore",
  parameters: {},
  execute: async () => {
    try {
      const info = await invoke<string>("get_system_info");
      return info;
    } catch (err) {
      return `Errore nel recupero info sistema: ${err}`;
    }
  },
});

registerTool({
  name: "run_command",
  description:
    "Esegue un comando shell sul computer. Può fare QUALSIASI cosa: cambiare luminosità, controllare WiFi, gestire file, impostazioni di sistema, installare programmi, etc. Usalo quando nessun altro tool è specifico per il compito. Su macOS usa comandi bash/zsh, su Windows usa cmd/powershell.",
  parameters: {
    command: {
      type: "string",
      description:
        "Il comando shell da eseguire. Esempi macOS: 'brightness 0.5' per luminosità, 'networksetup -setairportpower en0 off' per WiFi, 'pmset displaysleepnow' per spegnere schermo",
      required: true,
    },
    confirmed: {
      type: "boolean",
      description:
        "Se true, il comando viene eseguito anche se richiede conferma. Usare false di default, true solo dopo conferma utente.",
      required: false,
    },
  },
  execute: async (params) => {
    try {
      const result = await invoke<string>("run_command", {
        command: String(params.command),
        confirmed: params.confirmed === true,
      });
      return result;
    } catch (err) {
      return `${err}`;
    }
  },
});

registerTool({
  name: "run_applescript",
  description:
    "Esegue un AppleScript su macOS. Perfetto per controllare app, impostazioni di sistema, luminosità, volume, notifiche, finestre. Più potente dei comandi shell per interagire con le app macOS.",
  parameters: {
    script: {
      type: "string",
      description:
        'Lo script AppleScript. Esempi: \'tell application "System Events" to set dark mode to true\', \'set volume output volume 50\'',
      required: true,
    },
  },
  execute: async (params) => {
    try {
      const result = await invoke<string>("run_applescript", {
        script: String(params.script),
      });
      return result;
    } catch (err) {
      return `${err}`;
    }
  },
});

registerTool({
  name: "set_brightness",
  description: "Imposta la luminosità dello schermo (0-100)",
  parameters: {
    level: {
      type: "number",
      description: "Livello di luminosità da 0 (minimo) a 100 (massimo)",
      required: true,
    },
  },
  execute: async (params) => {
    try {
      const result = await invoke<string>("set_brightness", {
        level: Number(params.level),
      });
      return result;
    } catch (err) {
      return `Errore luminosità: ${err}`;
    }
  },
});
