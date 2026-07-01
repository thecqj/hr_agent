import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ChatCard, ProgressInfo } from "@/features/chat/types/chat";
import { sendChatMessage, closeSession as apiCloseSession, getSession, getHistory } from "@/features/chat/api/chat";

const SESSION_STORAGE_KEY = "chat-session-id";

function generateSessionId(): string {
  return crypto.randomUUID();
}

function loadSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveSessionId(id: string): void {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  } catch {
    // localStorage may be unavailable
  }
}

function clearSessionId(): void {
  try {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(() => loadSessionId());
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback((text: string) => {
    if (isProcessing) return;

    // Add user message
    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    // Track the current assistant message being built
    let assistantContent = "";
    let assistantCards: ChatCard[] | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      sessionId,
      (eventType, data) => {
        switch (eventType) {
          case "session": {
            // Server confirms/assigns session_id
            const newSessionId = data.session_id as string;
            setSessionId(newSessionId);
            saveSessionId(newSessionId);
            break;
          }

          case "thinking":
            assistantContent = (data.status as string) || "思考中...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  progress: { status: assistantContent },
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;

          case "intent":
            assistantContent = "正在处理您的请求...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              }
              return updated;
            });
            break;

          case "progress":
            assistantProgress = {
              status: (data.status as string) || "处理中...",
              evaluated_count: data.evaluated_count as number | undefined,
              total_count: data.total_count as number | undefined,
            };
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantProgress!.status,
                  progress: assistantProgress,
                };
              }
              return updated;
            });
            break;

          case "result":
            assistantContent = (data.reply_message as string) || "";
            assistantCards = data.cards as ChatCard[] | undefined;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  cards: assistantCards,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;

          case "error":
            assistantContent = `❌ ${(data.message as string) || "发生错误"}`;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;
        }
      },
      (error) => {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `❌ 连接中断：${error.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => {
          // Remove any in-progress assistant message
          const filtered = prev.filter(
            (m) => !(m.role === "assistant" && m.progress)
          );
          return [...filtered, errorMsg];
        });
        setIsProcessing(false);
      },
      () => {
        setIsProcessing(false);
        abortControllerRef.current = null;
      },
    );

    abortControllerRef.current = controller;
  }, [isProcessing, sessionId]);

  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsProcessing(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const closeSession = useCallback(async () => {
    // Abort any in-progress request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Call backend to close the session (triggers summary generation)
    if (sessionId) {
      try {
        await apiCloseSession(sessionId);
      } catch {
        // Non-blocking: session close failure doesn't prevent UI reset
      }
    }

    // Clear frontend state
    setMessages([]);
    setIsProcessing(false);

    // Generate new session_id for next conversation
    const newId = generateSessionId();
    setSessionId(newId);
    saveSessionId(newId);
  }, [sessionId]);

  /**
   * Check if the current session is still active (e.g., after page refresh).
   * If not, generate a new session ID.
   */
  const validateSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const info = await getSession(sessionId);
      if (info.has_history) {
        // Session exists — restore messages from backend
        try {
          const history = await getHistory(sessionId);
          if (history.messages.length > 0) {
            setMessages(history.messages.map((m) => ({
              role: m.role,
              content: m.content,
              cards: m.cards as ChatCard[] | undefined,
              timestamp: m.timestamp,
            })));
          }
        } catch {
          // History fetch failed — user starts with empty view, can still send messages
        }
      } else {
        // Session is no longer active or doesn't exist
        const newId = generateSessionId();
        setSessionId(newId);
        saveSessionId(newId);
      }
    } catch {
      // On error, keep current session_id — will be validated on next message
    }
  }, [sessionId]);

  return {
    messages,
    isProcessing,
    sessionId,
    sendMessage,
    disconnect,
    clearMessages,
    closeSession,
    validateSession,
  };
}

export type UseChatReturn = ReturnType<typeof useChat>;
