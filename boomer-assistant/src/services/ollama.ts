import type { OllamaMessage, OllamaTool } from "../types";

const OLLAMA_BASE = "http://localhost:11434";
const MODEL = "qwen2.5:7b";

const SYSTEM_PROMPT_IT = `Sei un assistente gentile e paziente per persone anziane che hanno poca dimestichezza con il computer.

REGOLE IMPORTANTI:
- Parla in modo SEMPLICE e CHIARO, come se parlassi con tua nonna
- Usa frasi CORTE
- NON usare termini tecnici. Se devi, spiegali subito
- Sii PAZIENTE e RASSICURANTE
- Se puoi risolvere un problema con un tool, USALO subito
- Rispondi sempre nella lingua dell'utente (italiano o inglese)
- Quando usi un tool, spiega cosa stai facendo in parole semplici
- Se qualcosa non funziona, rassicura l'utente e proponi un'alternativa

Hai accesso a strumenti per controllare TUTTO il computer:
- Audio: volume, dispositivi, diagnostica
- App: aprire Facebook, Zoom, WhatsApp, YouTube, email
- Sistema: info computer, luminosità schermo
- run_command: eseguire QUALSIASI comando shell (luminosità, WiFi, file, impostazioni...)
- run_applescript: controllare app macOS con AppleScript

IMPORTANTE: usa run_command o run_applescript per qualsiasi cosa non coperta dagli altri tool.
Per la luminosità su macOS usa: osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to true'
Per il WiFi: networksetup -setairportpower en0 off
Usali subito senza chiedere troppi dettagli tecnici all'utente.`;

const SYSTEM_PROMPT_EN = `You are a kind and patient assistant for elderly people who are not comfortable with computers.

IMPORTANT RULES:
- Speak SIMPLY and CLEARLY, as if talking to your grandma
- Use SHORT sentences
- DON'T use technical jargon. If you must, explain it immediately
- Be PATIENT and REASSURING
- If you can solve a problem with a tool, USE IT right away
- Always respond in the user's language (Italian or English)
- When using a tool, explain what you're doing in simple words
- If something doesn't work, reassure the user and suggest an alternative

You have tools to control the ENTIRE computer:
- Audio: volume, devices, diagnostics
- Apps: open Facebook, Zoom, WhatsApp, YouTube, email
- System: computer info, screen brightness
- run_command: execute ANY shell command (brightness, WiFi, files, settings...)
- run_applescript: control macOS apps with AppleScript

IMPORTANT: use run_command or run_applescript for anything not covered by other tools.
For brightness on macOS use: osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to true'
For WiFi: networksetup -setairportpower en0 off
Use them right away without asking too many technical details.`;

export function getSystemPrompt(locale: string): string {
  return locale === "it" ? SYSTEM_PROMPT_IT : SYSTEM_PROMPT_EN;
}

export async function checkOllamaHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${OLLAMA_BASE}/api/tags`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function* streamChat(
  messages: OllamaMessage[],
  tools?: OllamaTool[]
): AsyncGenerator<{ content?: string; tool_calls?: Array<{ function: { name: string; arguments: Record<string, unknown> } }> ; done: boolean }> {
  const body: Record<string, unknown> = {
    model: MODEL,
    messages,
    stream: true,
    options: {
      num_ctx: 4096,
      temperature: 0.7,
    },
  };

  if (tools && tools.length > 0) {
    body.tools = tools;
  }

  const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Ollama error: ${res.status} ${res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const json = JSON.parse(line);
        yield {
          content: json.message?.content,
          tool_calls: json.message?.tool_calls,
          done: json.done || false,
        };
      } catch {
        // skip malformed lines
      }
    }
  }
}

export async function chatComplete(
  messages: OllamaMessage[],
  tools?: OllamaTool[]
): Promise<{ content: string; tool_calls?: Array<{ function: { name: string; arguments: Record<string, unknown> } }> }> {
  let content = "";
  let toolCalls: Array<{ function: { name: string; arguments: Record<string, unknown> } }> | undefined;

  for await (const chunk of streamChat(messages, tools)) {
    if (chunk.content) content += chunk.content;
    if (chunk.tool_calls) toolCalls = chunk.tool_calls;
  }

  return { content, tool_calls: toolCalls };
}
