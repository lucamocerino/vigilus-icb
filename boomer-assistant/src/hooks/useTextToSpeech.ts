import { useState, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

interface UseTextToSpeechOptions {
  locale: string;
  onStart?: () => void;
  onEnd?: () => void;
}

export function useTextToSpeech({ locale, onStart, onEnd }: UseTextToSpeechOptions) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const unlistenRef = useRef<(() => void) | null>(null);

  const speak = useCallback(
    async (text: string) => {
      try {
        setIsSpeaking(true);
        onStart?.();

        const unlisten = await listen("piper-done", () => {
          setIsSpeaking(false);
          onEnd?.();
          unlistenRef.current?.();
          unlistenRef.current = null;
        });
        unlistenRef.current = unlisten;

        await invoke("speak_text", {
          text,
          language: locale === "it" ? "it" : "en",
        });
      } catch (err) {
        setIsSpeaking(false);
        onEnd?.();
        console.error("TTS error:", err);
      }
    },
    [locale, onStart, onEnd]
  );

  const stop = useCallback(async () => {
    try {
      await invoke("stop_speaking");
      setIsSpeaking(false);
      unlistenRef.current?.();
      unlistenRef.current = null;
      onEnd?.();
    } catch (err) {
      console.error("TTS stop error:", err);
    }
  }, [onEnd]);

  return { isSpeaking, speak, stop };
}
