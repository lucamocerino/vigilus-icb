import { useTranslation } from "../i18n";

interface StatusBarProps {
  ollamaConnected: boolean;
}

export function StatusBar({ ollamaConnected }: StatusBarProps) {
  const { locale, setLocale, t } = useTranslation();

  return (
    <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200">
      {/* Connection status */}
      <div className="flex items-center gap-2">
        <span
          className={`w-3 h-3 rounded-full ${ollamaConnected ? "bg-green-500" : "bg-red-500 animate-pulse"}`}
        />
        <span className="text-boomer-sm text-gray-600">
          {ollamaConnected ? t("status.ai_ready") : t("status.ai_loading")}
        </span>
      </div>

      {/* Language toggle */}
      <button
        onClick={() => setLocale(locale === "it" ? "en" : "it")}
        className="
          flex items-center gap-2 px-4 py-2
          bg-gray-100 hover:bg-gray-200
          rounded-full transition-colors
          text-boomer-sm font-medium text-gray-700
        "
        aria-label={t("settings.language")}
      >
        <span className="text-xl">{locale === "it" ? "🇮🇹" : "🇬🇧"}</span>
        <span>{locale === "it" ? "Italiano" : "English"}</span>
      </button>
    </div>
  );
}
