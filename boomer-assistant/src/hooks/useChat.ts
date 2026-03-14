import { useState, useCallback, useRef } from "react";
import type { Message, OllamaMessage, VoiceState } from "../types";
import { getSystemPrompt, checkOllamaHealth } from "../services/ollama";
import { runAgentLoop, type AgentEvent } from "../services/tools";

let messageCounter = 0;
function makeId(): string {
  return `msg-${Date.now()}-${++messageCounter}`;
}

export function useChat(locale: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ollamaConnected, setOllamaConnected] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const conversationRef = useRef<OllamaMessage[]>([]);

  const checkConnection = useCallback(async () => {
    const ok = await checkOllamaHealth();
    setOllamaConnected(ok);
    return ok;
  }, []);

  const addMessage = useCallback((role: Message["role"], content: string, toolName?: string) => {
    const msg: Message = { id: makeId(), role, content, timestamp: Date.now(), toolName };
    setMessages((prev) => [...prev, msg]);
    return msg;
  }, []);

  const sendMessage = useCallback(
    async (text: string): Promise<string> => {
      if (!text.trim()) return "";

      setIsProcessing(true);
      setVoiceState("processing");
      addMessage("user", text);

      if (conversationRef.current.length === 0) {
        conversationRef.current.push({
          role: "system",
          content: getSystemPrompt(locale),
        });
      }

      conversationRef.current.push({ role: "user", content: text });

      const assistantMsgId = makeId();
      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, role: "assistant", content: "", timestamp: Date.now() },
      ]);

      let fullResponse = "";

      try {
        const handleEvent = (event: AgentEvent) => {
          switch (event.type) {
            case "token":
              fullResponse += event.content;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsgId ? { ...m, content: fullResponse } : m))
              );
              break;
            case "tool_call":
              addMessage("tool", `🔧 ${event.name}(${JSON.stringify(event.args)})`, event.name);
              break;
            case "tool_result":
              addMessage("tool", `✅ ${event.result}`, event.name);
              break;
            case "done":
              fullResponse = event.content;
              break;
            case "error":
              addMessage("system", `⚠️ ${event.message}`);
              break;
          }
        };

        fullResponse = await runAgentLoop(conversationRef.current, handleEvent);

        conversationRef.current.push({ role: "assistant", content: fullResponse });

        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, content: fullResponse } : m))
        );
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : String(err);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: `❌ ${errMsg}` } : m
          )
        );
        fullResponse = "";
      }

      setIsProcessing(false);
      setVoiceState("idle");
      return fullResponse;
    },
    [locale, addMessage]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    conversationRef.current = [];
  }, []);

  return {
    messages,
    addMessage,
    isProcessing,
    ollamaConnected,
    voiceState,
    setVoiceState,
    sendMessage,
    checkConnection,
    clearHistory,
  };
}
