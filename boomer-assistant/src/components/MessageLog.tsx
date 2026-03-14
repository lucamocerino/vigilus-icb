import { useEffect, useRef } from "react";
import type { Message } from "../types";

interface MessageLogProps {
  messages: Message[];
}

export function MessageLog({ messages }: MessageLogProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) return null;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`
            animate-slide-up
            flex ${msg.role === "user" ? "justify-end" : "justify-start"}
          `}
        >
          <div
            className={`
              max-w-[85%] rounded-2xl px-5 py-3
              text-boomer-base leading-relaxed
              ${msg.role === "user"
                ? "bg-primary-600 text-white rounded-br-md"
                : msg.role === "tool"
                  ? "bg-amber-50 text-amber-900 border border-amber-200 rounded-bl-md text-base"
                  : msg.role === "system"
                    ? "bg-gray-100 text-gray-600 rounded-bl-md text-base italic"
                    : "bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md"
              }
            `}
          >
            {msg.role === "tool" && msg.toolName && (
              <span className="text-sm font-semibold text-amber-700 block mb-1">
                🔧 {msg.toolName}
              </span>
            )}
            {msg.role === "user" && (
              <span className="text-xs opacity-75 block mb-1">🎤 Hai detto:</span>
            )}
            <p className="whitespace-pre-wrap">{msg.content}</p>
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
