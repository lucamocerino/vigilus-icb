import { useTranslation } from "../i18n";
import type { VoiceState } from "../types";

interface VoiceButtonProps {
  voiceState: VoiceState;
  onToggle: () => void;
  disabled?: boolean;
}

export function VoiceButton({ voiceState, onToggle, disabled }: VoiceButtonProps) {
  const { t } = useTranslation();

  const isListening = voiceState === "listening";
  const isProcessing = voiceState === "processing";
  const isSpeaking = voiceState === "speaking";
  const isActive = isListening || isProcessing || isSpeaking;
  const isBusy = isProcessing || isSpeaking;

  const label = isListening
    ? t("voice.listening")
    : isProcessing
      ? t("voice.processing")
      : isSpeaking
        ? t("voice.speaking")
        : t("voice.press_to_talk");

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onClick={!disabled && !isBusy ? onToggle : undefined}
        disabled={disabled || isBusy}
        className={`
          relative w-32 h-32 rounded-full
          flex items-center justify-center
          transition-all duration-300 ease-in-out
          shadow-lg hover:shadow-xl
          focus:outline-none focus:ring-4 focus:ring-primary-200
          ${disabled ? "bg-gray-300 cursor-not-allowed" : ""}
          ${isActive ? "bg-red-500 scale-110" : "bg-primary-600 hover:bg-primary-700"}
          ${isListening ? "animate-pulse-slow" : ""}
        `}
        aria-label={label}
      >
        {/* Ripple effect when listening */}
        {isListening && (
          <>
            <span className="absolute inset-0 rounded-full bg-red-400 animate-ping opacity-20" />
            <span className="absolute inset-2 rounded-full bg-red-400 animate-ping opacity-10 animation-delay-150" />
          </>
        )}

        {/* Microphone icon */}
        <svg
          className="w-14 h-14 text-white relative z-10"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          {isProcessing ? (
            // Spinner
            <path
              className="animate-spin origin-center"
              strokeLinecap="round"
              d="M12 2a10 10 0 0 1 10 10"
            />
          ) : isSpeaking ? (
            // Speaker icon
            <>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.95 6.05a8 8 0 010 11.9" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 5L6 9H2v6h4l5 4V5z" />
            </>
          ) : (
            // Microphone
            <>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 01-14 0v-2" />
              <path strokeLinecap="round" d="M12 19v4M8 23h8" />
            </>
          )}
        </svg>
      </button>

      <span
        className={`
          text-boomer-base font-medium
          ${isActive ? "text-red-600" : "text-gray-600"}
          transition-colors duration-200
        `}
      >
        {label}
      </span>
    </div>
  );
}
