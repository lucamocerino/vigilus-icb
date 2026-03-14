import { useState, useCallback, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { VoiceState } from "../types";

interface UseVoiceRecognitionOptions {
  locale: string;
  onResult: (text: string) => void;
  onError?: (error: string) => void;
}

export function useVoiceRecognition({ locale, onResult, onError }: UseVoiceRecognitionOptions) {
  const [state, setState] = useState<VoiceState>("idle");
  const unlistenRef = useRef<(() => void) | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    unlistenRef.current?.();
    unlistenRef.current = null;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const startListening = useCallback(async () => {
    try {
      cleanup();
      setState("listening");

      const unlisten = await listen<string>("whisper-result", (event) => {
        console.log("[boomer] whisper-result received:", event.payload);
        cleanup();
        setState("idle");
        onResult(event.payload);
      });
      unlistenRef.current = unlisten;

      console.log("[boomer] Invoking start_listening...");
      await invoke("start_listening", { language: locale === "it" ? "it" : "en" });
      console.log("[boomer] start_listening OK");
    } catch (err) {
      console.error("[boomer] start_listening FAILED:", err);
      cleanup();
      setState("idle");
      onError?.(err instanceof Error ? err.message : String(err));
    }
  }, [locale, onResult, onError, cleanup]);

  const stopListening = useCallback(async () => {
    try {
      setState("processing");
      console.log("[boomer] Invoking stop_listening...");
      await invoke("stop_listening");
      console.log("[boomer] stop_listening OK, waiting for whisper-result...");

      // Timeout di sicurezza: 30s per la trascrizione
      timeoutRef.current = setTimeout(() => {
        console.warn("[boomer] Whisper timeout after 30s");
        cleanup();
        setState("idle");
        onError?.("Trascrizione troppo lenta, riprova.");
      }, 30000);
    } catch (err) {
      console.error("[boomer] stop_listening FAILED:", err);
      cleanup();
      setState("idle");
      onError?.(err instanceof Error ? err.message : String(err));
    }
  }, [onError, cleanup]);

  return { state, startListening, stopListening };
}
