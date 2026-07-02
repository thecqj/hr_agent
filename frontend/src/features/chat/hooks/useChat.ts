import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ProgressInfo, ToolStatusInfo } from "@/features/chat/types/chat";
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
    let assistantToolStatus: ToolStatusInfo | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      sessionId,
      (eventType, data) => {
        switch (eventType) {
          case "session": {
            const newSessionId = data.session_id as string;
            setSessionId(newSessionId);
            saveSessionId(newSessionId);
            break;
          }

          case "tool_start": {
            const toolName = data.tool as string;
            assistantToolStatus = { tool: toolName, status: "started" };
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent || `正在使用 ${toolName} 查询...`,
                  toolStatus: assistantToolStatus,
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: `正在使用 ${toolName} 查询...`,
                  toolStatus: assistantToolStatus,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "tool_end": {
            // Don't update UI on tool_end — wait for text_delta or result
            break;
          }

          case "text_delta": {
            const delta = data.content as string;
            assistantContent += delta;
            assistantToolStatus = undefined; // text output means tool is done
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "progress": {
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
          }

          case "result": {
            const replyMessage = (data.reply_message as string) || "";
            if (replyMessage) {
              assistantContent = replyMessage;
            }
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "error": {
            assistantContent = `❌ ${(data.message as string) || "发生错误"}`;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;
          }
        }
      },
      (error) => {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `❌ 连接中断：${error.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => {
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
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (sessionId) {
      try {
        await apiCloseSession(sessionId);
      } catch {
        // Non-blocking
      }
    }

    setMessages([]);
    setIsProcessing(false);

    const newId = generateSessionId();
    setSessionId(newId);
    saveSessionId(newId);
  }, [sessionId]);

  const validateSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const info = await getSession(sessionId);
      if (info.has_history) {
        try {
          const history = await getHistory(sessionId);
          if (history.messages.length > 0) {
            setMessages(history.messages.map((m) => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp,
            })));
          }
        } catch {
          // History fetch failed — start with empty view
        }
      } else {
        const newId = generateSessionId();
        setSessionId(newId);
        saveSessionId(newId);
      }
    } catch {
      // Keep current session_id
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
