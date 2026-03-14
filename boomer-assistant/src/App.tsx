import { useEffect, useCallback } from "react";
import { useTranslation } from "./i18n";
import { useChat } from "./hooks/useChat";
import { useVoiceRecognition } from "./hooks/useVoiceRecognition";
import { useTextToSpeech } from "./hooks/useTextToSpeech";
import { VoiceButton } from "./components/VoiceButton";
import { MessageLog } from "./components/MessageLog";
import { StatusBar } from "./components/StatusBar";

// Register built-in tools
import "./services/builtin-tools";

function App() {
  const { locale, t } = useTranslation();
  const {
    messages,
    addMessage,
    isProcessing,
    ollamaConnected,
    voiceState,
    setVoiceState,
    sendMessage,
    checkConnection,
  } = useChat(locale);

  const { speak } = useTextToSpeech({
    locale,
    onStart: () => setVoiceState("speaking"),
    onEnd: () => setVoiceState("idle"),
  });

  const handleVoiceResult = useCallback(
    async (text: string) => {
      if (!text.trim() || text.startsWith("[Errore")) {
        setVoiceState("idle");
        return;
      }
      setVoiceState("processing");
      const response = await sendMessage(text);
      if (response) {
        await speak(response);
      }
    },
    [sendMessage, speak, setVoiceState]
  );

  const { startListening, stopListening } = useVoiceRecognition({
    locale,
    onResult: handleVoiceResult,
    onError: (err) => {
      console.error("Voice error:", err);
      addMessage("system", `⚠️ Errore voce: ${err}`);
      setVoiceState("idle");
    },
  });

  const handleToggleVoice = useCallback(async () => {
    if (voiceState === "listening") {
      try {
        setVoiceState("processing");
        await stopListening();
      } catch (err) {
        addMessage("system", `⚠️ Stop failed: ${err}`);
        setVoiceState("idle");
      }
    } else {
      try {
        setVoiceState("listening");
        await startListening();
      } catch (err) {
        addMessage("system", `⚠️ Start failed: ${err}`);
        setVoiceState("idle");
      }
    }
  }, [voiceState, startListening, stopListening, setVoiceState, addMessage]);

  // Check Ollama on mount
  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  // Welcome message
  useEffect(() => {
    if (messages.length === 0 && ollamaConnected) {
      // Add welcome message without sending to AI
    }
  }, [ollamaConnected, messages.length]);

  return (
    <div className="flex flex-col h-screen bg-surface-light">
      <StatusBar ollamaConnected={ollamaConnected} />

      {/* Header */}
      <div className="text-center py-6 px-4">
        <h1 className="text-boomer-2xl font-bold text-gray-800">
          {t("app.title")}
        </h1>
        <p className="text-boomer-base text-gray-500 mt-1">
          {t("app.subtitle")}
        </p>
      </div>

      {/* Messages */}
      <MessageLog messages={messages} />

      {/* Welcome if empty */}
      {messages.length === 0 && (
        <div className="flex-1 flex items-center justify-center px-8">
          <p className="text-boomer-lg text-gray-400 text-center">
            {t("messages.welcome")}
          </p>
        </div>
      )}

      {/* Voice button area */}
      <div className="py-8 flex justify-center">
        <VoiceButton
          voiceState={voiceState}
          onToggle={handleToggleVoice}
          disabled={!ollamaConnected || isProcessing}
        />
      </div>
    </div>
  );
}

export default App;
