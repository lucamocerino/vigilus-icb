import type { ToolDefinition, OllamaTool, OllamaMessage, ToolCall } from "../types";

const toolRegistry = new Map<string, ToolDefinition>();

export function registerTool(tool: ToolDefinition) {
  toolRegistry.set(tool.name, tool);
}

export function getRegisteredTools(): ToolDefinition[] {
  return Array.from(toolRegistry.values());
}

export function getToolByName(name: string): ToolDefinition | undefined {
  return toolRegistry.get(name);
}

export function toolsToOllamaFormat(): OllamaTool[] {
  return getRegisteredTools().map((tool) => ({
    type: "function",
    function: {
      name: tool.name,
      description: tool.description,
      parameters: {
        type: "object",
        properties: Object.fromEntries(
          Object.entries(tool.parameters).map(([key, param]) => [
            key,
            {
              type: param.type,
              description: param.description,
              ...(param.enum ? { enum: param.enum } : {}),
            },
          ])
        ),
        required: Object.entries(tool.parameters)
          .filter(([, param]) => param.required !== false)
          .map(([key]) => key),
      },
    },
  }));
}

export async function executeTool(call: ToolCall): Promise<string> {
  const tool = toolRegistry.get(call.name);
  if (!tool) return `Errore: strumento "${call.name}" non trovato`;

  try {
    return await tool.execute(call.arguments);
  } catch (err) {
    return `Errore nell'esecuzione di ${call.name}: ${err instanceof Error ? err.message : String(err)}`;
  }
}

const MAX_ITERATIONS = 8;

export type AgentCallback = (event: AgentEvent) => void;

export type AgentEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: string }
  | { type: "done"; content: string }
  | { type: "error"; message: string };

export async function runAgentLoop(
  messages: OllamaMessage[],
  onEvent: AgentCallback
): Promise<string> {
  const tools = toolsToOllamaFormat();
  const conversationMessages = [...messages];
  let fullResponse = "";

  for (let i = 0; i < MAX_ITERATIONS; i++) {
    const { streamChat } = await import("./ollama");
    let iterContent = "";
    let toolCalls: Array<{ function: { name: string; arguments: Record<string, unknown> } }> | undefined;

    for await (const chunk of streamChat(conversationMessages, tools)) {
      if (chunk.content) {
        iterContent += chunk.content;
        onEvent({ type: "token", content: chunk.content });
      }
      if (chunk.tool_calls) {
        toolCalls = chunk.tool_calls;
      }
    }

    if (!toolCalls || toolCalls.length === 0) {
      fullResponse = iterContent;
      onEvent({ type: "done", content: fullResponse });
      return fullResponse;
    }

    conversationMessages.push({
      role: "assistant",
      content: iterContent,
      tool_calls: toolCalls,
    });

    for (const tc of toolCalls) {
      const toolCall: ToolCall = {
        name: tc.function.name,
        arguments: tc.function.arguments,
      };

      onEvent({ type: "tool_call", name: toolCall.name, args: toolCall.arguments });
      const result = await executeTool(toolCall);
      onEvent({ type: "tool_result", name: toolCall.name, result });

      conversationMessages.push({
        role: "tool",
        content: result,
      });
    }
  }

  onEvent({ type: "error", message: "Troppe iterazioni, mi fermo qui." });
  return fullResponse || "Mi dispiace, ho dovuto fermarmi perché ci stavo mettendo troppo.";
}
