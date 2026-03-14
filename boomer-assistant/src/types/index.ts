export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: number;
  toolName?: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, ToolParam>;
  execute: (params: Record<string, unknown>) => Promise<string>;
}

export interface ToolParam {
  type: "string" | "number" | "boolean";
  description: string;
  required?: boolean;
  enum?: string[];
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface OllamaMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  tool_calls?: Array<{
    function: { name: string; arguments: Record<string, unknown> };
  }>;
}

export interface OllamaTool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, { type: string; description: string; enum?: string[] }>;
      required: string[];
    };
  };
}

export type VoiceState = "idle" | "listening" | "processing" | "speaking";
