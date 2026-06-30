import { useAuthStore } from "@/features/auth/store/authStore";
import type { SessionInfo } from "@/features/chat/types/chat";

const API_BASE = "/api";

/**
 * Send a chat message and return an AbortController for SSE streaming.
 * Uses native fetch + ReadableStream for POST-based SSE
 * (EventSource API only supports GET).
 */
export function sendChatMessage(
  message: string,
  sessionId: string | null,
  onEvent: (eventType: string, data: Record<string, unknown>) => void,
  onError: (error: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();
  const token = useAuthStore.getState().token;

  fetch(`${API_BASE}/chat/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(new Error(`HTTP ${response.status}`));
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError(new Error("No response body"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr) as Record<string, unknown>;
              if (currentEvent === "done") {
                onDone();
              } else {
                onEvent(currentEvent, data);
              }
            } catch {
              // Skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }

      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err);
      }
    });

  return controller;
}

/**
 * Close a chat session — marks it as inactive and triggers summary generation.
 */
export async function closeSession(sessionId: string): Promise<void> {
  const token = useAuthStore.getState().token;

  const response = await fetch(`${API_BASE}/chat/session/close`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

/**
 * Query the current active session for the user.
 * If session_id is provided, checks that specific session's status.
 * Otherwise, returns the most recent active session.
 */
export async function getSession(sessionId?: string): Promise<SessionInfo> {
  const token = useAuthStore.getState().token;
  const params = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";

  const response = await fetch(`${API_BASE}/chat/session${params}`, {
    method: "GET",
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json() as Promise<SessionInfo>;
}
